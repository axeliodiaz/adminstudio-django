"""View-facing services for the FAQ app.

Expose functions that return schemas or simple dicts for consumption by views.
"""

from uuid import UUID

from django.db import IntegrityError
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from apps.faqs.models import FAQItem, Section
from apps.faqs.schemas import AdminFAQItemSchema, AdminSectionSchema


def get_published_faq() -> dict:
    """Return all published FAQ items grouped by sections.

    Returns:
        dict: FAQPublicSchema as dict with sections and their FAQ items.
    """
    sections = Section.objects.all().order_by("order", "name")
    result = []

    for section in sections:
        faq_items = (
            FAQItem.objects.filter(section=section, is_published=True, is_removed=False)
            .order_by("order", "question")
            .select_related("section")
        )

        if faq_items.exists():
            section_data = {
                "id": str(section.id),
                "name": section.name,
                "slug": section.slug,
                "description": section.description,
                "order": section.order,
                "items": [
                    {
                        "id": str(item.id),
                        "question": item.question,
                        "answer": item.answer,  # Markdown content
                        "order": item.order,
                    }
                    for item in faq_items
                ],
            }
            result.append(section_data)

    return {"sections": result}


def _serialize_admin_section(section: Section, faq_count: int | None = None) -> dict:
    if faq_count is None:
        faq_count = section.faq_items.filter(is_removed=False).count()
    payload = {
        "id": section.id,
        "name": section.name,
        "slug": section.slug,
        "description": section.description or "",
        "order": section.order,
        "faq_count": faq_count,
        "created": section.created,
        "modified": section.modified,
    }
    return AdminSectionSchema.model_validate(payload).model_dump(mode="json")


def _serialize_admin_item(item: FAQItem) -> dict:
    payload = {
        "id": item.id,
        "section_id": item.section_id,
        "section_name": item.section.name,
        "question": item.question,
        "answer": item.answer,
        "order": item.order,
        "is_published": item.is_published,
        "created": item.created,
        "modified": item.modified,
    }
    return AdminFAQItemSchema.model_validate(payload).model_dump(mode="json")


def _unique_slug(*, name: str, current_id: UUID | None = None) -> str:
    base = slugify(name) or "seccion"
    slug = base
    suffix = 2
    queryset = Section.objects.all()
    if current_id:
        queryset = queryset.exclude(id=current_id)
    while queryset.filter(slug=slug).exists():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def list_admin_sections(*, search: str | None = None) -> list[dict]:
    queryset = Section.objects.annotate(
        faq_count=Count("faq_items", filter=Q(faq_items__is_removed=False))
    ).order_by("order", "name")
    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(name__icontains=term) | Q(slug__icontains=term) | Q(description__icontains=term)
        )
    return [_serialize_admin_section(section, faq_count=section.faq_count) for section in queryset]


def get_admin_section(*, section_id: str | UUID) -> dict:
    section = get_object_or_404(Section, id=section_id)
    return _serialize_admin_section(section)


def create_admin_section(*, data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("El nombre de la sección es obligatorio.")

    slug = (data.get("slug") or "").strip() or _unique_slug(name=name)
    description = data.get("description")
    if description is None:
        description = ""
    order = data.get("order")
    if order is None:
        max_order = Section.objects.aggregate(Max("order")).get("order__max") or 0
        order = max_order + 1

    if Section.objects.filter(name__iexact=name).exists():
        raise ValueError("Ya existe una sección con ese nombre.")
    if Section.objects.filter(slug=slug).exists():
        raise ValueError("Ya existe una sección con ese slug.")

    try:
        section = Section.objects.create(
            name=name,
            slug=slug,
            description=description,
            order=int(order),
        )
    except IntegrityError as exc:
        raise ValueError("Ya existe una sección con ese nombre o slug.") from exc
    return _serialize_admin_section(section)


def update_admin_section(*, section_id: str | UUID, data: dict) -> dict:
    section = get_object_or_404(Section, id=section_id)

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("El nombre de la sección es obligatorio.")
        if Section.objects.filter(name__iexact=name).exclude(id=section.id).exists():
            raise ValueError("Ya existe una sección con ese nombre.")
        section.name = name
        if "slug" not in data or not (data.get("slug") or "").strip():
            section.slug = _unique_slug(name=name, current_id=section.id)

    if "slug" in data and (data.get("slug") or "").strip():
        slug = str(data.get("slug")).strip()
        if Section.objects.filter(slug=slug).exclude(id=section.id).exists():
            raise ValueError("Ya existe una sección con ese slug.")
        section.slug = slug
    if "description" in data:
        section.description = data.get("description") or ""
    if "order" in data and data.get("order") is not None:
        section.order = int(data["order"])

    try:
        section.save()
    except IntegrityError as exc:
        raise ValueError("Ya existe una sección con ese nombre o slug.") from exc
    return _serialize_admin_section(section)


def list_admin_faq_items(
    *,
    search: str | None = None,
    section_id: str | UUID | None = None,
    status: str | None = None,
) -> list[dict]:
    queryset = (
        FAQItem.objects.select_related("section")
        .filter(is_removed=False)
        .order_by("section__order", "order", "question")
    )
    if section_id:
        queryset = queryset.filter(section_id=section_id)
    if status == "published":
        queryset = queryset.filter(is_published=True)
    elif status == "draft":
        queryset = queryset.filter(is_published=False)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(question__icontains=term)
            | Q(answer__icontains=term)
            | Q(section__name__icontains=term)
        )
    return [_serialize_admin_item(item) for item in queryset]


def get_admin_faq_item(*, item_id: str | UUID) -> dict:
    item = get_object_or_404(
        FAQItem.objects.select_related("section"),
        id=item_id,
        is_removed=False,
    )
    return _serialize_admin_item(item)


def create_admin_faq_item(*, data: dict) -> dict:
    section_id = data.get("section_id")
    if not section_id:
        raise ValueError("La sección es obligatoria.")
    question = (data.get("question") or "").strip()
    if not question:
        raise ValueError("La pregunta es obligatoria.")
    answer = data.get("answer")
    if answer is None or not str(answer).strip():
        raise ValueError("La respuesta es obligatoria.")

    section = get_object_or_404(Section, id=section_id)
    order = data.get("order")
    if order is None:
        max_order = (
            FAQItem.objects.filter(section=section, is_removed=False)
            .aggregate(Max("order"))
            .get("order__max")
            or 0
        )
        order = max_order + 1

    item = FAQItem.objects.create(
        section=section,
        question=question,
        answer=str(answer).strip(),
        order=int(order),
        is_published=bool(data.get("is_published", True)),
    )
    return _serialize_admin_item(item)


def update_admin_faq_item(*, item_id: str | UUID, data: dict) -> dict:
    item = get_object_or_404(
        FAQItem.objects.select_related("section"),
        id=item_id,
        is_removed=False,
    )

    if "section_id" in data:
        section_id = data.get("section_id")
        if not section_id:
            raise ValueError("La sección es obligatoria.")
        item.section = get_object_or_404(Section, id=section_id)
    if "question" in data:
        question = (data.get("question") or "").strip()
        if not question:
            raise ValueError("La pregunta es obligatoria.")
        item.question = question
    if "answer" in data:
        answer = data.get("answer")
        if answer is None or not str(answer).strip():
            raise ValueError("La respuesta es obligatoria.")
        item.answer = str(answer).strip()
    if "order" in data and data.get("order") is not None:
        item.order = int(data["order"])
    if "is_published" in data:
        item.is_published = bool(data.get("is_published"))

    item.save()
    item.refresh_from_db()
    return _serialize_admin_item(item)
