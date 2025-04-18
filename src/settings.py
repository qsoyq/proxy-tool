from pydantic import BaseSettings


class AppSettings(BaseSettings):  # type:ignore
    api_prefix: str = "/api"
    basic_auth_user: str = "root"
    basic_auth_passwd: str = "example"

    ics_fetch_vlrgg_match_time_semaphore: int = 15
