from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Section(UUIDModel, TimeStampedModel):
    """Section for organizing FAQ items (e.g., Horarios, Perfil, Instructores)."""

    name = models.CharField(max_length=100, unique=True, help_text="Nombre de la sección")
    slug = models.SlugField(max_length=100, unique=True, help_text="Slug único para la sección")
    description = models.TextField(
        blank=True, default="", help_text="Descripción opcional de la sección"
    )
    order = models.PositiveIntegerField(default=0, help_text="Orden de visualización")

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"

    def __str__(self):
        return self.name


class FAQItem(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """FAQ Item with question, answer (markdown), and section."""

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="faq_items",
        help_text="Sección a la que pertenece esta pregunta",
    )
    question = models.CharField(max_length=255, help_text="Pregunta")
    answer = models.TextField(help_text="Respuesta en formato Markdown")
    order = models.PositiveIntegerField(default=0, help_text="Orden dentro de la sección")
    is_published = models.BooleanField(
        default=True, help_text="Si está publicado, aparecerá en el endpoint público"
    )

    class Meta:
        ordering = ["section__order", "order", "question"]
        verbose_name = "Pregunta Frecuente"
        verbose_name_plural = "Preguntas Frecuentes"
        indexes = [
            models.Index(fields=["section", "is_published", "order"]),
        ]

    def __str__(self):
        return f"{self.section.name}: {self.question}"
