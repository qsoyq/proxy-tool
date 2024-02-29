from pydantic import BaseSettings


class AppSettings(BaseSettings):  # type:ignore
    api_prefix: str = "/api"
