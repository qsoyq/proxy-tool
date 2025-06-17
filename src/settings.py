import time
from datetime import datetime
from pydantic import BaseSettings


run_at_ts = int(time.time())
run_at = datetime.fromtimestamp(run_at_ts).strftime(r"%Y-%m-%d %H:%M:%S")
version = "0.1.39"


class AppSettings(BaseSettings):  # type:ignore
    api_prefix: str = "/api"
    basic_auth_user: str = "root"
    basic_auth_passwd: str = "example"

    ics_fetch_vlrgg_match_time_semaphore: int = 15
    gc_trigger_memory_percent_limit: float = 80
    gc_trigger_memory_percent_interval: int = 30
