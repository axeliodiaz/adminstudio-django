"""View-facing services for the public docs API.

Only published, non-removed sections and pages are exposed.
"""

from django.shortcuts import get_object_or_404

from apps.docs.models import DocAudience, DocPage, DocSection
from apps.docs.schemas import DocPageDetailSchema, DocsIndexSchema


def _page_summary(page: DocPage) -> dict:
    return {
        "id": page.id,
        "title": page.title,
        "slug": page.slug,
        "summary": page.summary or "",
        "order": page.order,
        "related_app_route": page.related_app_route or "",
    }


def _published_pages_qs():
    return DocPage.objects.filter(is_published=True, is_removed=False).order_by("order", "title")


def get_published_docs_index(
    *,
    audience: str | None = None,
    allowed_audiences: frozenset[str],
) -> dict:
    """Return published docs grouped by audience, then section."""
    sections = (
        DocSection.objects.filter(
            is_published=True,
            is_removed=False,
            audience__in=allowed_audiences,
        )
        .prefetch_related("pages")
        .order_by("audience", "order", "title")
    )
    if audience:
        sections = sections.filter(audience=audience)

    grouped: dict[str, list[dict]] = {choice.value: [] for choice in DocAudience}
    for section in sections:
        pages = [
            _page_summary(page)
            for page in section.pages.all()
            if page.is_published and not page.is_removed
        ]
        pages.sort(key=lambda item: (item["order"], item["title"]))
        if not pages:
            continue
        grouped[section.audience].append(
            {
                "id": section.id,
                "title": section.title,
                "slug": section.slug,
                "audience": section.audience,
                "order": section.order,
                "pages": pages,
            }
        )

    audiences = []
    for choice in DocAudience:
        sections_payload = grouped.get(choice.value) or []
        if not sections_payload:
            continue
        audiences.append(
            {
                "id": choice.value,
                "label": choice.label,
                "sections": sections_payload,
            }
        )

    return DocsIndexSchema.model_validate({"audiences": audiences}).model_dump(mode="json")


def get_published_doc_page(
    *,
    section_slug: str,
    page_slug: str,
    allowed_audiences: frozenset[str],
) -> dict:
    """Return a published page by section and page slug, or 404."""
    page = get_object_or_404(
        _published_pages_qs().select_related("section"),
        slug=page_slug,
        section__slug=section_slug,
        section__is_published=True,
        section__is_removed=False,
        section__audience__in=allowed_audiences,
    )
    payload = {
        "id": page.id,
        "title": page.title,
        "slug": page.slug,
        "summary": page.summary or "",
        "body": page.body or "",
        "order": page.order,
        "related_app_route": page.related_app_route or "",
        "modified": page.modified,
        "section": {
            "id": page.section.id,
            "title": page.section.title,
            "slug": page.section.slug,
            "audience": page.section.audience,
        },
    }
    return DocPageDetailSchema.model_validate(payload).model_dump(mode="json")
