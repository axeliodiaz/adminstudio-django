"""Constants for the schedules app.

These constants are shared across the schedules app (models, services, etc.).
"""

# Schedule statuses
SCHEDULE_STATUS_DRAFT = "draft"
SCHEDULE_STATUS_SCHEDULED = "scheduled"
SCHEDULE_STATUS_COMPLETED = "completed"
SCHEDULE_STATUS_CANCELED = "canceled"
SCHEDULE_STATUSES = (
    SCHEDULE_STATUS_DRAFT,
    SCHEDULE_STATUS_SCHEDULED,
    SCHEDULE_STATUS_COMPLETED,
    SCHEDULE_STATUS_CANCELED,
)
