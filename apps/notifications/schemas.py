import uuid

from pydantic import BaseModel

from apps.users.schemas import UserSchema


class Notification(BaseModel):
    id: uuid.UUID
    subject: str
    message: str
    user_id: uuid.UUID
    recipient_list: list[UserSchema]

    def get_recipient_mail_list(self):
        return [recipient.email for recipient in self.recipient_list]
