from pydantic import BaseModel, Field
from schemas.adapter import HttpUrl


class AuthorSchema(BaseModel):
    login: str | None = Field(None, examples=['github-actions[bot]'])
    id: int = Field(...)
    node_id: str | None = Field(None, examples=['RA_kwDOM3UDoc4Q91P0'])
    avatar_url: str | None = Field(None, examples=['https://avatars.githubusercontent.com/in/15368?v=4'])
    gravatar_id: str | None = Field(None, examples=[''])
    url: HttpUrl | None = Field(None, examples=['https://api.github.com/users/github-actions%5Bbot%5D'])
    html_url: HttpUrl | None = Field(None, examples=['https://github.com/apps/github-actions'])
    followers_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/followers']
    )
    following_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/following{/other_user}']
    )
    gists_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/gists{/gist_id}']
    )
    starred_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/starred{/owner}{/repo}']
    )
    subscriptions_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/subscriptions']
    )
    organizations_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/orgs']
    )
    repos_url: HttpUrl | None = Field(None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/repos'])
    events_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/events{/privacy}']
    )
    received_events_url: HttpUrl | None = Field(
        None, examples=['https://api.github.com/users/github-actions%5Bbot%5D/received_events']
    )
    type: str | None = Field(None, examples=['Bot'])
    user_view_type: str | None = Field(None, examples=['public'])
    site_admin: bool | None = Field(None, examples=[False])
