from pydantic import BaseModel, Field, model_validator


class JSONFeedItemAuthor(BaseModel):
    url: str | None = Field(None)
    name: str | None = Field(None)
    avatar: str | None = Field(None)


class JSONFeedItem(BaseModel):
    id: str = Field(...)
    url: str | None = Field(None)
    external_url: str | None = Field(None)
    title: str | None = Field(None)
    content_html: str | None = Field(None)
    content_text: str | None = Field(None)

    author: JSONFeedItemAuthor
    date_published: str = Field("")

    @model_validator(mode="after")
    def check_content(cls, values):
        content_html = values.content_html
        content_text = values.content_text
        if content_html is None and content_text is None:
            raise ValueError("Either content_html or content_text must have at least one valid value.")
        return values


class JSONFeed(BaseModel):
    """
    https://www.jsonfeed.org/version/1/
    """

    version: str = Field("https://jsonfeed.org/version/1")
    title: str = Field(...)
    home_page_url: str | None = Field(None)
    feed_url: str | None = Field(None)
    description: str | None = Field(None)
    user_comment: str | None = Field(None)
    next_url: str | None = Field(None)
    icon: str | None = Field(None)
    favicon: str | None = Field(None)
    author: JSONFeedItemAuthor | None = Field(None)
    expired: bool | None = Field(None)
    items: list[JSONFeedItem]
