from enum import Enum

from pydantic import BaseModel, Field


class GithubIssueState(str, Enum):
    open = "open"
    closed = "closed"
    all = "all"


class GithubIssueSort(str, Enum):
    created = "created"
    updated = "updated"
    comments = "comments"


class GithubIssueDirection(str, Enum):
    asc = "asc"
    desc = "desc"


class GithubIssue(BaseModel):
    id: int
    url: str
    repository_url: str
    html_url: str
    number: int
    title: str
    state: str
    locked: bool | None = Field(None)
    body: str | None = Field(None)
    created_at: str
    updated_at: str | None = Field(None)
