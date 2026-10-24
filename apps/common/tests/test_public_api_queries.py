"""Query budgets for public PulseFit Studio API payloads."""

import pytest
from django.urls import reverse
from model_bakery import baker

from apps.docs.models import DocAudience
from apps.docs.services import get_published_docs_index
from apps.faqs.services import get_published_faq
from apps.plans import constants
from apps.plans.models import Plan
from apps.plans.services import get_plans
from apps.studios.services import get_list_studios, get_studio_branding


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }


@pytest.mark.django_db
class TestPublicApiQueryBudgets:
    def test_faq_public_two_queries(self, django_assert_num_queries, api_client):
        section = baker.make("faqs.Section", requires_staff=False)
        baker.make("faqs.FAQItem", section=section, is_published=True)
        with django_assert_num_queries(2):
            get_published_faq()
        with django_assert_num_queries(0):
            get_published_faq()
        response = api_client.get(reverse("faqs-list"))
        assert response.status_code == 200
        assert "Cache-Control" in response

    def test_plans_list_two_queries(self, django_assert_num_queries):
        Plan.objects.create(
            name="Demo",
            type=constants.PLAN_TYPE_MEMBERSHIP,
            price=1000,
            is_active=True,
        )
        with django_assert_num_queries(2):
            get_plans()
        with django_assert_num_queries(0):
            get_plans()

    def test_studios_list_bounded_queries(self, django_assert_num_queries):
        address = baker.make("studios.Address")
        studio = baker.make(
            "studios.Studio", address=address, is_active=True, is_default_brand=True
        )
        location = baker.make("studios.Location", studio=studio, is_active=True)
        baker.make("studios.Room", location=location)
        with django_assert_num_queries(3):
            get_list_studios()
        with django_assert_num_queries(0):
            get_list_studios()

    def test_branding_bounded_queries(self, django_assert_num_queries):
        studio = baker.make("studios.Studio", is_active=True, is_default_brand=True)
        baker.make("studios.StudioBranding", studio=studio)
        baker.make("studios.StudioBranding", studio=None)
        with django_assert_num_queries(2):
            get_studio_branding()
        with django_assert_num_queries(0):
            get_studio_branding()

    def test_docs_index_bounded_queries(self, django_assert_num_queries):
        allowed = frozenset(DocAudience.values)
        with django_assert_num_queries(2):
            get_published_docs_index(allowed_audiences=allowed)
        with django_assert_num_queries(0):
            get_published_docs_index(allowed_audiences=allowed)

    def test_healthcheck_live_no_database(self, django_assert_num_queries, api_client):
        with django_assert_num_queries(0):
            response = api_client.get(reverse("healthcheck-live"))
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
