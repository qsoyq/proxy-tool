from pydantic import BaseModel, Field, model_validator, HttpUrl


class JSONFeedAuthor(BaseModel):
    url: HttpUrl | None = Field(None)
    name: str | None = Field(None)
    avatar: str | None = Field(None)


class JSONFeedAttachment(BaseModel):
    url: HttpUrl = Field(...)
    mime_type: str = Field(...)
    title: str | None = Field(None)
    size_in_bytes: float | None = Field(None)
    duration_in_seconds: float | None = Field(None)


class JSONFeedItem(BaseModel):
    id: str = Field(...)
    url: HttpUrl | None = Field(None)
    external_url: HttpUrl | None = Field(None)
    title: str | None = Field(None)
    content_html: str | None = Field(None)
    content_text: str | None = Field(None)
    summary: str | None = Field(None)
    image: HttpUrl | None = Field(None)
    banner_image: HttpUrl | None = Field(None)
    date_published: str | None = Field(None, examples=["2010-02-07T14:04:00-05:00"])
    date_modified: str | None = Field(None, examples=["2010-02-07T14:04:00-05:00"])
    tags: list[str] | None = Field(None)

    author: JSONFeedAuthor | None = Field(None)

    attachments: list[JSONFeedAttachment] | None = Field(None)

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
    home_page_url: HttpUrl | None = Field(None)
    feed_url: HttpUrl | None = Field(None)
    description: str | None = Field(None)
    user_comment: str | None = Field(None)
    next_url: HttpUrl | None = Field(None)
    icon: str | None = Field(None)
    favicon: str | None = Field(None)
    author: JSONFeedAuthor | None = Field(None)
    expired: bool | None = Field(None)
    items: list[JSONFeedItem]
