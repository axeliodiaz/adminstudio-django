"""Coverage, editorial safety and audience regressions for CYC-423."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from apps.faqs.management.commands.seed_people_inventory_faq import SECTIONS
from apps.faqs.models import FAQItem, Section


@pytest.mark.django_db
def test_seed_is_additive_idempotent_and_repairs_access():
    call_command("seed_people_inventory_faq")
    section = Section.objects.get(slug="personas-staff")
    item = FAQItem.objects.filter(section=section).first()
    item.answer = "Studio-edited answer"
    item.is_published = False
    item.save()
    section.requires_staff = False
    section.save()
    removed = FAQItem.objects.filter(section__slug="inventario-staff").first()
    removed.delete()
    call_command("seed_people_inventory_faq")
    item.refresh_from_db()
    section.refresh_from_db()
    assert section.requires_staff is True
    assert item.answer == "Studio-edited answer"
    assert item.is_published is False
    assert FAQItem.all_objects.filter(question=removed.question).count() == 1
    assert FAQItem.all_objects.get(pk=removed.pk).is_removed is True
    for data in SECTIONS:
        assert FAQItem.all_objects.filter(section__slug=data["slug"]).count() == len(data["items"])


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["anonymous", "member", "coach", "staff", "admin"])
def test_only_admins_receive_new_guides(api_client, role):
    call_command("seed_people_inventory_faq")
    if role != "anonymous":
        user = get_user_model().objects.create_user(
            username=f"guide-{role}",
            password="synthetic-only",
            is_staff=role in {"staff", "admin"},
            is_superuser=role == "admin",
        )
        if role == "coach":
            from model_bakery import baker

            baker.make("instructors.Instructor", user=user)
        api_client.force_authenticate(user=user)
    response = api_client.get(reverse("faqs-list"))
    assert response.status_code == 200
    visible = {s["slug"] for s in response.data["sections"]}
    for data in SECTIONS:
        assert (data["slug"] in visible) == (role == "admin")


def test_guides_limit_claims_to_delivered_features():
    people = " ".join(answer for _, answer in SECTIONS[0]["items"])
    inventory = " ".join(answer for _, answer in SECTIONS[1]["items"])
    assert "directorio de consulta" in people
    assert "No incluye edición" in people
    assert "Sin conteo inicial significa desconocido, no cero" in inventory
    assert "no inventa movimientos históricos" in inventory
    assert "no una asignación automática" in inventory


@pytest.mark.django_db
def test_stock_seed_updates_only_original_answer_and_preserves_publication():
    from apps.faqs.management.commands.seed_people_inventory_faq import PREVIOUS_ANSWERS

    call_command("seed_people_inventory_faq")
    for question, answers in PREVIOUS_ANSWERS.items():
        item = FAQItem.objects.get(question=question)
        item.answer = answers[0]
        item.is_published = False
        item.save()
    call_command("seed_people_inventory_faq")
    for question in PREVIOUS_ANSWERS:
        item = FAQItem.objects.get(question=question)
        assert item.answer == dict(SECTIONS[1]["items"])[question]
        assert item.is_published is False
