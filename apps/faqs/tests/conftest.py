"""FAQ CRUD tests use an empty catalogue, independently of shipped policy data."""

import pytest
from apps.faqs.models import FAQItem, Section


@pytest.fixture(autouse=True)
def empty_faq_catalogue(db):
    FAQItem.all_objects.all().delete()
    Section.objects.all().delete()
