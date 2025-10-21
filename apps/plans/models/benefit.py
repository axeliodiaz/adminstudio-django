from mongoengine import Document, StringField, BooleanField


class Benefit(Document):
    name = StringField(required=True, unique=True, max_length=100)
    description = StringField(max_length=255, null=True)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "benefits",
        "ordering": ["name"],
        "indexes": ["name", "is_active"],
    }

    def __str__(self):
        return self.name
