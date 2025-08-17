from pydantic import BaseModel, HttpUrl, Field


class App(BaseModel):
    screenshotUrls: list[HttpUrl] | None = Field(None)
    ipadScreenshotUrls: list[HttpUrl] | None = Field(None)
    artistViewUrl: HttpUrl | None = Field(None)
    artworkUrl512: HttpUrl | None = Field(None)
    artworkUrl100: HttpUrl | None = Field(None)
    artworkUrl60: HttpUrl | None = Field(None)
    supportedDevices: list[str] | None = Field(None)
    minimumOsVersion: str | None = Field(None)
    version: str | None = Field(None)
    fileSizeBytes: str | None = Field(None)
    formattedPrice: str | None = Field(None)
    artistId: int | None = Field(None)
    artistName: str | None = Field(None)
    price: float | None = Field(None)
    currency: str | None = Field(None)
    bundleId: str | None = Field(None)
    description: str | None = Field(None)
    trackViewUrl: HttpUrl | None = Field(None)


class SearchAppListSchema(BaseModel):
    data: list[App]
