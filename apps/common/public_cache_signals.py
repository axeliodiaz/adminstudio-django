"""Invalidate public API cache namespaces when content changes."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.public_cache import invalidate
from apps.docs.models import DocPage, DocSection
from apps.faqs.models import FAQItem, Section
from apps.legal.models import LegalDocument
from apps.plans.models import Benefit, Plan, PromoCode
from apps.studios.models import Address, Location, Room, Studio, StudioBranding


def _connect(model, namespace: str) -> None:
    receiver(
        post_save, sender=model, dispatch_uid=f"public-cache-save-{namespace}-{model._meta.label}"
    )(lambda **_: invalidate(namespace))
    receiver(
        post_delete, sender=model, dispatch_uid=f"public-cache-del-{namespace}-{model._meta.label}"
    )(lambda **_: invalidate(namespace))


for _model in (Section, FAQItem):
    _connect(_model, "faqs")

for _model in (Plan, Benefit, PromoCode):
    _connect(_model, "plans")

for _model in (Studio, StudioBranding, Address, Location, Room):
    _connect(_model, "studios")

_connect(LegalDocument, "legal")

for _model in (DocSection, DocPage):
    _connect(_model, "docs")
