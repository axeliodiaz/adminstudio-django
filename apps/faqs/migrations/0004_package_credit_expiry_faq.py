"""Add the owner's grandfathered package-credit policy, without replacing existing FAQs."""

import uuid
from django.db import migrations

ITEM_ID = uuid.UUID("b66c0979-3502-433f-af46-de18097178a5")


def forward(apps, schema_editor):
    Section = apps.get_model("faqs", "Section")
    FAQItem = apps.get_model("faqs", "FAQItem")
    section, _ = Section.objects.get_or_create(
        slug="creditos-de-paquetes",
        defaults={"name": "Créditos de paquetes", "order": 50, "requires_staff": False},
    )
    FAQItem.objects.get_or_create(
        pk=ITEM_ID,
        defaults={
            "section": section,
            "question": "¿Cuándo vencen los créditos de mis paquetes?",
            "answer": "Los créditos que ya tenías antes de activar esta regla conservan su saldo sin vencimiento. "
            "Las compras nuevas guardan la vigencia propia del paquete al comprarse y su fecha de vencimiento al activarse; "
            "verás la fecha prevista antes de comprar y la definitiva en tu historial. "
            "Para reservar, la clase debe comenzar antes de que venza el crédito, en hora de Santiago. "
            "Usamos primero los créditos válidos con vencimiento más cercano. Comprar varios paquetes no amplía su vigencia. "
            "Cancelar dentro del plazo permitido devuelve el crédito a su paquete original y no extiende su vencimiento. "
            "Si el estudio cancela una clase y el paquete ya venció, corresponde un crédito de reemplazo sin vencimiento, uno por reserva reembolsada y registrado aparte. "
            "La regla no requiere un proceso nocturno ni elimina tus saldos anteriores.",
            "is_published": True,
            "order": 0,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("faqs", "0003_section_requires_staff"),
        ("wallets", "0009_planpurchase_credit_expiry_enabled_and_more"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
