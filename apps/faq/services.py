"""View-facing services for the FAQ app.

Expose functions that return schemas or simple dicts for consumption by views.
"""

from apps.faq.models import Section, FAQItem
from apps.faq.schemas import FAQPublicSchema


def get_published_faq() -> dict:
    """Return all published FAQ items grouped by sections.

    Returns:
        dict: FAQPublicSchema as dict with sections and their FAQ items.
    """
    sections = Section.objects.all().order_by("order", "name")
    result = []

    for section in sections:
        faq_items = (
            FAQItem.objects.filter(section=section, is_published=True, is_deleted=False)
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
