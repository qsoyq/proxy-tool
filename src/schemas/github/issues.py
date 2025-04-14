from enum import Enum
from pydantic import BaseModel


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
    locked: str
    body: str
    created_at: str
    updated_at: str
