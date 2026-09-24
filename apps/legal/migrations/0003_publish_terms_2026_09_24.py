"""Publish the 2026-09-24 terms and conditions (CYC-94)."""

from datetime import date

from django.db import migrations

TERMS_CONTENT = "# Términos y Condiciones de Compra y Uso - PulseFit Studio\nVigencia: 24 de septiembre de 2026\n\nAl comprar un plan o reservar una clase en PulseFit Studio (PulseFit SpA, RUT 77.777.777-7, domicilio Calle Ficticia 123, Oficina 4, Santiago de Chile), aceptas estos términos.\n\n## 1. Planes disponibles\nLos precios están en pesos chilenos e incluyen IVA.\n\nMembresías (acceso ilimitado a clases durante 30 días desde la activación):\n- Ilimitado Glitter - $89.000. Incluye 2 guest passes, prioridad de reserva, café de especialidad post-ride y toalla con monograma.\n- Premium Oscar - $69.000. Incluye 1 guest pass, prioridad de reserva, café post-ride y toalla.\n- Estudiante Remix - $39.000. Para estudiantes con credencial estudiantil o certificado de alumno regular vigente. Incluye café post-ride y toalla.\n\nPaquetes de clases:\n- Smart 8 Sprints - $49.000. 8 clases, válidas por 30 días desde la activación. Incluye café post-ride y toalla.\n- Drop-in Cameo - $12.000. 1 clase, válida por 1 día. Incluye café post-ride y toalla.\n\nEl detalle vigente de cada plan se publica en la página de Planes. Si algo difiere entre estos términos y la página de Planes al momento de tu compra, se aplica lo publicado en la página de Planes.\n\n## 2. Activación, vigencia y acumulación\n- El plan se activa al confirmarse el pago y la vigencia se cuenta desde ese día.\n- Las clases de un paquete que no se usen dentro de su vigencia vencen y no se reembolsan ni se extienden.\n- Si compras una membresía mientras tienes una activa, los días nuevos se suman al final de la vigente; no se superponen ni se pierden.\n- Los planes no tienen renovación automática. Cada compra es un pago único.\n\n## 3. Pago\nEl pago se realiza en línea al finalizar la compra, con los medios disponibles en la plataforma. Puedes usar códigos promocionales vigentes; no son acumulables entre sí salvo que se indique lo contrario.\n\n## 4. Pack de primera vez\nCuando se ofrezca un pack de primera vez, es solo para personas sin compras previas en PulseFit, se compra solo, en cantidad 1, y no se puede regalar.\n\n## 5. Reservas y cancelaciones\n- Cada reserva usa 1 clase de tu billetera; con membresía activa no se descuentan clases.\n- Puedes cancelar sin costo hasta 2 horas antes del inicio de la clase y la clase vuelve a tu billetera.\n- Si cancelas con menos de 2 horas de anticipación o no asistes, la clase se considera usada.\n- Si PulseFit cancela una clase, te devolvemos la clase a la billetera y te avisamos por correo.\n- PulseFit puede cambiar al instructor de una clase; si eso pasa te avisaremos cuando sea posible.\n\n## 6. Lista de espera\nSi una clase está llena, puedes unirte a la lista de espera. Cuando se libera un spot, se ofrece en orden y tienes 15 minutos para aceptarlo; si no, pasa a la siguiente persona.\n\n## 7. Guest passes\nLos guest passes incluidos en tu plan te permiten invitar a otra persona a una clase. La invitación es válida por 14 días. Si cancelas la reserva del invitado dentro del plazo de cancelación sin costo, el guest pass vuelve a tu billetera.\n\n## 8. Gift cards\nPuedes regalar un plan como gift card. La gift card vence 365 días después de emitida y se activa en la cuenta de quien la canjea. No es canjeable por dinero.\n\n## 9. Beneficios\nLos beneficios (prioridad de reserva, café post-ride, toalla, etc.) se mantienen mientras el plan que los otorga esté vigente. La prioridad de reserva te da acceso preferente y alertas cuando se liberan cupos. Los beneficios físicos están sujetos a disponibilidad en el estudio.\n\n## 10. Transferencias y reembolsos\nLos planes son personales e intransferibles, salvo como gift card. No hay reembolsos de planes comprados, excepto cuando PulseFit cancela el servicio o cuando la ley lo exija (Ley N° 19.496 sobre Protección de los Derechos de los Consumidores).\n\n## 11. Cambios a los planes y a estos términos\nPulseFit puede modificar precios, planes y estos términos. Los cambios no afectan los planes ya comprados, que conservan las condiciones vigentes al momento de la compra. La versión vigente y su fecha se publican en esta página.\n\n## 12. Contacto\nDudas o reclamos: contacto@pulsefit.example o en recepción del estudio.\n"


def publish_terms(apps, schema_editor):
    LegalDocument = apps.get_model("legal", "LegalDocument")
    LegalDocument.objects.filter(document_type="terms_and_conditions", language="es").update(
        is_published=False
    )
    LegalDocument.objects.update_or_create(
        slug="terminos-y-condiciones-2026-09-24",
        defaults={
            "document_type": "terms_and_conditions",
            "title": "Términos y Condiciones de Compra y Uso",
            "content": TERMS_CONTENT,
            "language": "es",
            "version": "2026-09-24",
            "effective_date": date(2026, 9, 24),
            "is_published": True,
            "order": 0,
        },
    )


def rollback_terms(apps, schema_editor):
    LegalDocument = apps.get_model("legal", "LegalDocument")
    LegalDocument.objects.filter(slug="terminos-y-condiciones-2026-09-24").delete()
    LegalDocument.objects.filter(
        document_type="terms_and_conditions", language="es", version="1.0"
    ).update(is_published=True)


class Migration(migrations.Migration):
    dependencies = [("legal", "0002_chilean_privacy_policy")]
    operations = [migrations.RunPython(publish_terms, rollback_terms)]
