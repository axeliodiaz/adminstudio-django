# Generated for CYC-441 (reports app: precomputed metric tables)

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("instructors", "0006_instructor_is_coordinator"),
        ("schedules", "0007_cyc79_hot_path_indexes"),
        ("studios", "0006_studiobranding"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassMetrics",
            fields=[
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                (
                    "id",
                    model_utils.fields.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("date", models.DateField(db_index=True)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("is_canceled", models.BooleanField(default=False)),
                ("capacity", models.PositiveIntegerField(default=0)),
                ("booked", models.PositiveIntegerField(default=0)),
                ("attended", models.PositiveIntegerField(default=0)),
                ("missed", models.PositiveIntegerField(default=0)),
                ("cancelled", models.PositiveIntegerField(default=0)),
                ("waitlist_count", models.PositiveIntegerField(default=0)),
                ("waitlist_converted", models.PositiveIntegerField(default=0)),
                ("occupancy_rate", models.FloatField(default=0.0)),
                (
                    "rating",
                    models.DecimalField(blank=True, decimal_places=1, max_digits=2, null=True),
                ),
                ("rating_count", models.PositiveIntegerField(default=0)),
                ("computed_at", models.DateTimeField(auto_now=True)),
                (
                    "instructor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="class_metrics",
                        to="instructors.instructor",
                    ),
                ),
                (
                    "schedule",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_metrics",
                        to="schedules.schedule",
                    ),
                ),
                (
                    "studio",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="class_metrics",
                        to="studios.studio",
                    ),
                ),
            ],
            options={
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="DailyMetrics",
            fields=[
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                (
                    "id",
                    model_utils.fields.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("date", models.DateField(db_index=True)),
                ("classes_total", models.PositiveIntegerField(default=0)),
                ("classes_canceled", models.PositiveIntegerField(default=0)),
                ("spots_capacity", models.PositiveIntegerField(default=0)),
                (
                    "reservations_booked",
                    models.PositiveIntegerField(
                        default=0, help_text="Occupied spots: reserved, attended or missed."
                    ),
                ),
                ("reservations_attended", models.PositiveIntegerField(default=0)),
                ("reservations_missed", models.PositiveIntegerField(default=0)),
                ("reservations_cancelled", models.PositiveIntegerField(default=0)),
                (
                    "occupancy_rate",
                    models.FloatField(default=0.0, help_text="Booked / capacity, percent."),
                ),
                (
                    "attendee_ids",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Member ids who attended a class this day; powers retention reports.",
                    ),
                ),
                (
                    "waitlist_entries",
                    models.PositiveIntegerField(
                        default=0, help_text="Waitlist entries created this day."
                    ),
                ),
                (
                    "waitlist_converted",
                    models.PositiveIntegerField(
                        default=0, help_text="Conversions on classes held this day."
                    ),
                ),
                ("revenue", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("purchases_count", models.PositiveIntegerField(default=0)),
                ("first_time_buyers", models.PositiveIntegerField(default=0)),
                ("returning_buyers", models.PositiveIntegerField(default=0)),
                ("discount_total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("promo_uses", models.PositiveIntegerField(default=0)),
                (
                    "revenue_by_plan",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='{"<plan name>": {"revenue": <clp>, "count": <n>}} for the day.',
                    ),
                ),
                ("gift_cards_sold", models.PositiveIntegerField(default=0)),
                ("gift_cards_redeemed", models.PositiveIntegerField(default=0)),
                ("guest_passes_issued", models.PositiveIntegerField(default=0)),
                ("guest_passes_claimed", models.PositiveIntegerField(default=0)),
                ("guest_passes_attended", models.PositiveIntegerField(default=0)),
                ("referrals_signed_up", models.PositiveIntegerField(default=0)),
                ("referrals_converted", models.PositiveIntegerField(default=0)),
                ("notifications_sent", models.PositiveIntegerField(default=0)),
                ("link_clicks", models.PositiveIntegerField(default=0)),
                ("ratings_count", models.PositiveIntegerField(default=0)),
                ("rating_avg", models.FloatField(blank=True, null=True)),
                ("new_members", models.PositiveIntegerField(default=0)),
                ("computed_at", models.DateTimeField(auto_now=True)),
                (
                    "studio",
                    models.ForeignKey(
                        blank=True,
                        help_text="Studio scope. NULL is the global all-studios row (only scope written today).",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_metrics",
                        to="studios.studio",
                    ),
                ),
            ],
            options={
                "ordering": ["-date"],
            },
        ),
        migrations.AddIndex(
            model_name="classmetrics",
            index=models.Index(fields=["instructor", "date"], name="classmetrics_coach_date_idx"),
        ),
        migrations.AddIndex(
            model_name="classmetrics",
            index=models.Index(fields=["studio", "date"], name="classmetrics_scope_date_idx"),
        ),
        migrations.AddIndex(
            model_name="dailymetrics",
            index=models.Index(fields=["studio", "date"], name="dailymetrics_scope_date_idx"),
        ),
        migrations.AddConstraint(
            model_name="dailymetrics",
            constraint=models.UniqueConstraint(
                condition=models.Q(("studio__isnull", True)),
                fields=("date",),
                name="uniq_dailymetrics_global_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="dailymetrics",
            constraint=models.UniqueConstraint(
                condition=models.Q(("studio__isnull", False)),
                fields=("date", "studio"),
                name="uniq_dailymetrics_studio_date",
            ),
        ),
    ]
