import uuid
from datetime import datetime
from mongoengine import Document, UUIDField, BooleanField, DateTimeField


class UUIDModel(Document):
    """
    Base document that uses a UUID as primary key.
    """

    id = UUIDField(primary_key=True, default=uuid.uuid4)

    meta = {"abstract": True}


class TimeStampedModel(Document):
    """
    Adds created_at and updated_at timestamps.
    """

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {"abstract": True}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)


class SoftDeletableModel(Document):
    """
    Adds soft delete behavior via an `is_deleted` flag.
    """

    is_deleted = BooleanField(default=False)

    meta = {"abstract": True}

    def delete(self, soft: bool = True, **write_concern):
        if soft:
            self.is_deleted = True
            self.save()
        else:
            super().delete(**write_concern)

    @classmethod
    def active(cls):
        """Return only documents not soft-deleted."""
        return cls.objects(is_deleted=False)
