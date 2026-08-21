from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class LegalDocumentType(models.TextChoices):
    """Types of legal documents."""

    TERMS_AND_CONDITIONS = "terms_and_conditions", "Términos y Condiciones"
    PRIVACY_POLICY = "privacy_policy", "Política de Privacidad"
    WAIVER = "waiver", "Renuncia de Responsabilidad"
    COOKIE_POLICY = "cookie_policy", "Política de Cookies"
    REFUND_POLICY = "refund_policy", "Política de Reembolsos"


class LegalDocument(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """Legal document (Terms & Conditions, Privacy Policy, etc.)."""

    document_type = models.CharField(
        max_length=50,
        choices=LegalDocumentType.choices,
        help_text="Tipo de documento legal",
    )
    title = models.CharField(max_length=255, help_text="Título del documento")
    slug = models.SlugField(max_length=255, unique=True, help_text="Slug único para el documento")
    content = models.TextField(help_text="Contenido del documento en formato Markdown")
    language = models.CharField(
        max_length=10,
        default="es",
        help_text="Código de idioma (es, en, etc.)",
    )
    version = models.CharField(
        max_length=20,
        default="1.0",
        help_text="Versión del documento (ej: 1.0, 1.1, 2.0)",
    )
    effective_date = models.DateField(
        help_text="Fecha de vigencia del documento",
    )
    is_published = models.BooleanField(
        default=True,
        help_text="Si está publicado, aparecerá en el endpoint público",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Orden de visualización (para múltiples documentos del mismo tipo)",
    )

    class Meta:
        ordering = ["document_type", "order", "-effective_date", "title"]
        verbose_name = "Documento Legal"
        verbose_name_plural = "Documentos Legales"
        unique_together = [["document_type", "language", "version"]]
        indexes = [
            models.Index(fields=["document_type", "is_published", "language"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()}: {self.title} ({self.language})"
