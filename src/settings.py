from pydantic import BaseSettings


class AppSettings(BaseSettings):
    api_prefix: str = ''
