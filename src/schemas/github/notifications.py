from pydantic import BaseModel, Field
from schemas.github import AuthorSchema


class NotificationRepositorySchema(BaseModel):
    id: int
    node_id: str
    name: str
    full_name: str
    html_url: str
    description: str
    fork: bool
    owner: AuthorSchema


class NotificationSubjectSchema(BaseModel):
    title: str
    url: str
    latest_comment_url: str | None
    type: str


class NotificationSchema(BaseModel):
    id: str
    unread: bool
    reason: str
    updated_at: str = Field(..., examples=['2025-10-06T13:29:36Z'])
    last_read_at: str | None = Field(None, examples=['2025-10-06T13:29:36Z'])
    url: str
    subscription_url: str

    subject: NotificationSubjectSchema
    repository: NotificationRepositorySchema
