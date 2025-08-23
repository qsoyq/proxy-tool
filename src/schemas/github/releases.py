from pydantic import BaseModel, HttpUrl, Field
from schemas.github import AuthorSchema


class AssetSchema(BaseModel):
    uploader: AuthorSchema | None = Field(None)
    url: HttpUrl = Field(..., description="指向资源详细内容 JSON 的 url")
    id: int = Field(...)
    node_id: str | None = Field(None, examples=["RA_kwDOM3UDoc4Q91P0"])
    name: str | None = Field(None, examples=["iRingo.WeatherKit.plugin"])
    label: str | None = Field(None, examples=[""])
    content_type: str | None = Field(None, examples=["application/octet-stream"])
    state: str | None = Field(None, examples=["uploaded"])
    size: int | None = Field(None, examples=[4461])
    digest: str | None = Field(
        None, examples=["sha256:e3814adb94e8207fe0c6125983b1336e6f2ea5afb217ac66c52c683c64b1eef1"]
    )
    download_count: int | None = Field(None, examples=[1387])
    created_at: str | None = Field(None, examples=["2025-08-21T02:47:04Z"])
    updated_at: str | None = Field(None, examples=["2025-08-21T02:47:04Z"])
    browser_download_url: str | None = Field(
        None, examples=["https://github.com/NSRingo/WeatherKit/releases/download/v1.9.8/iRingo.WeatherKit.plugin"]
    )


class ReleaseSchema(BaseModel):
    id: int
    author: AuthorSchema | None = Field(None)
    url: HttpUrl | None = Field(None, examples=["https://api.github.com/repos/NSRingo/WeatherKit/releases/241379237"])
    assets_url: HttpUrl | None = Field(
        None, examples=["https://api.github.com/repos/NSRingo/WeatherKit/releases/241379237/assets"]
    )
    upload_url: HttpUrl | None = Field(
        None, examples=["https://uploads.github.com/repos/NSRingo/WeatherKit/releases/241379237/assets{?name,label}"]
    )
    html_url: HttpUrl | None = Field(None, examples=["https://github.com/NSRingo/WeatherKit/releases/tag/v1.9.8"])
    node_id: str | None = Field(None, examples=["RE_kwDOM3UDoc4OYyel"])
    tag_name: str | None = Field(None, examples=["v1.9.8"])
    target_commitish: str | None = Field(None, examples=["main"])
    name: str | None = Field(None, examples=["v1.9.8"])
    draft: bool | None = Field(None, examples=[False])
    immutable: bool | None = Field(None, examples=[False])
    prerelease: bool | None = Field(None, examples=[False])
    created_at: str | None = Field(None, examples=["2025-08-21T02:46:11Z"])
    updated_at: str | None = Field(None, examples=["2025-08-21T02:46:11Z"])
    published_at: str | None = Field(None, examples=["2025-08-21T02:46:11Z"])
    assets: list[AssetSchema] | None = Field(None)
    tarball_url: HttpUrl | None = Field(
        None, examples=["https://uploads.github.com/repos/NSRingo/WeatherKit/releases/241379237/assets{?name,label}"]
    )
    zipball_url: HttpUrl | None = Field(
        None, examples=["https://api.github.com/repos/NSRingo/WeatherKit/zipball/v1.9.8"]
    )
    body: str | None = Field(
        None,
        examples=[
            "### 🛠️ Bug Fixes\n  * 修复 v1.9.6 版 `DataSets` (数据集) 设置功能导致的 `历史趋势对比数据` 丢失问题"
        ],
    )
