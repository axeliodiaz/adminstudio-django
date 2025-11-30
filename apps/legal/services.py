"""View-facing services for the legal app.

Expose functions that return schemas or simple dicts for consumption by views.
"""

from apps.legal.models import LegalDocument, LegalDocumentType


def get_published_legal_document(document_type: str, language: str = "es") -> dict | None:
    """Return the latest published legal document of a specific type and language.

    Args:
        document_type: Type of document (e.g., 'terms_and_conditions', 'privacy_policy')
        language: Language code (default: 'es')

    Returns:
        dict: Legal document data or None if not found.
    """
    try:
        document = (
            LegalDocument.objects.filter(
                document_type=document_type,
                language=language,
                is_published=True,
                is_removed=False,
            )
            .order_by("-effective_date", "-order")
            .first()
        )

        if not document:
            return None

        return {
            "id": str(document.id),
            "document_type": document.document_type,
            "title": document.title,
            "slug": document.slug,
            "content": document.content,
            "language": document.language,
            "version": document.version,
            "effective_date": document.effective_date.isoformat(),
            "last_updated": document.modified.isoformat(),
        }
    except Exception:
        return None


def get_all_published_legal_documents(language: str = "es") -> dict:
    """Return all published legal documents grouped by type.

    Args:
        language: Language code (default: 'es')

    Returns:
        dict: Dictionary with document types as keys and document data as values.
    """
    # Get all documents and then filter to get the latest one per type
    all_documents = LegalDocument.objects.filter(
        language=language,
        is_published=True,
        is_removed=False,
    ).order_by("document_type", "-effective_date", "-order")

    result = {}
    seen_types = set()
    for document in all_documents:
        if document.document_type not in seen_types:
            seen_types.add(document.document_type)
            result[document.document_type] = {
                "id": str(document.id),
                "document_type": document.document_type,
                "title": document.title,
                "slug": document.slug,
                "content": document.content,
                "language": document.language,
                "version": document.version,
                "effective_date": document.effective_date.isoformat(),
                "last_updated": document.modified.isoformat(),
            }

    return result


def get_legal_document_by_slug(slug: str) -> dict | None:
    """Return a published legal document by its slug.

    Args:
        slug: Document slug

    Returns:
        dict: Legal document data or None if not found.
    """
    try:
        document = LegalDocument.objects.get(
            slug=slug,
            is_published=True,
            is_removed=False,
        )

        return {
            "id": str(document.id),
            "document_type": document.document_type,
            "title": document.title,
            "slug": document.slug,
            "content": document.content,
            "language": document.language,
            "version": document.version,
            "effective_date": document.effective_date.isoformat(),
            "last_updated": document.modified.isoformat(),
        }
    except LegalDocument.DoesNotExist:
        return None
