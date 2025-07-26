from pydantic import BaseModel, Field


class JSONFeedItemAuthor(BaseModel):
    url: str = Field("")
    name: str = Field("")
    avatar: str = Field("")


class JSONFeedItem(BaseModel):
    author: JSONFeedItemAuthor
    url: str = Field("")
    title: str = Field("")
    id: str = Field("")
    date_published: str = Field("")
    content_html: str = Field("")


class JSONFeed(BaseModel):
    version: str = Field("https://jsonfeed.org/version/1")
    title: str = Field("")
    description: str = Field("")
    home_page_url: str = Field("")
    feed_url: str = Field("")
    icon: str = Field("")
    favicon: str = Field("")
    items: list[JSONFeedItem]
