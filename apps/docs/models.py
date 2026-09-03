from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.docs.sanitize import sanitize_html


class DocAudience(models.TextChoices):
    MEMBER = "member", "Miembros"
    ADMIN = "admin", "Admin"
    COACH = "coach", "Coach"
    PLATFORM = "platform", "Plataforma"


class DocSection(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """Group of help articles aimed at one product audience."""

    audience = models.CharField(
        max_length=20,
        choices=DocAudience.choices,
        default=DocAudience.MEMBER,
        help_text="Audiencia a la que está dirigida esta sección",
    )
    title = models.CharField(max_length=160, help_text="Título de la sección")
    slug = models.SlugField(max_length=160, unique=True, help_text="Slug único de la sección")
    order = models.PositiveIntegerField(default=0, help_text="Orden de visualización")
    is_published = models.BooleanField(
        default=False,
        help_text="Si está publicado, aparecerá en el índice público",
    )

    class Meta:
        ordering = ["audience", "order", "title"]
        verbose_name = "Sección de documentación"
        verbose_name_plural = "Secciones de documentación"
        indexes = [
            models.Index(fields=["audience", "is_published", "order"]),
        ]

    def __str__(self):
        return f"{self.get_audience_display()}: {self.title}"


class DocPage(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """A single help article. Body is HTML edited in Django admin."""

    section = models.ForeignKey(
        DocSection,
        on_delete=models.CASCADE,
        related_name="pages",
        help_text="Sección a la que pertenece este artículo",
    )
    title = models.CharField(max_length=255, help_text="Título del artículo")
    slug = models.SlugField(max_length=255, help_text="Slug único dentro de la sección")
    summary = models.CharField(
        max_length=400,
        blank=True,
        default="",
        help_text="Resumen corto para el índice",
    )
    body = models.TextField(blank=True, default="", help_text="Cuerpo HTML del artículo")
    order = models.PositiveIntegerField(default=0, help_text="Orden dentro de la sección")
    is_published = models.BooleanField(
        default=False,
        help_text="Si está publicado, aparecerá en el endpoint público",
    )
    related_app_route = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Ruta de la app relacionada, por ejemplo #classes",
    )

    class Meta:
        ordering = ["section__order", "order", "title"]
        verbose_name = "Artículo de documentación"
        verbose_name_plural = "Artículos de documentación"
        constraints = [
            models.UniqueConstraint(
                fields=["section", "slug"],
                name="docs_docpage_section_slug_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["section", "is_published", "order"]),
        ]

    def __str__(self):
        return f"{self.section.title}: {self.title}"

    def save(self, *args, **kwargs):
        self.body = sanitize_html(self.body)
        super().save(*args, **kwargs)
