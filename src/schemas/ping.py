import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from pydantic import BaseModel, Field, validator
from settings import run_at, run_at_ts, version


def get_default_memory() -> "MemoryUsage":
    pid = os.getpid()
    process = psutil.Process(pid)
    memory = psutil.virtual_memory()
    used = process.memory_info().rss
    total = memory.total
    available = memory.available
    max_ = get_memory_max()

    body = {
        "used": f"{used/1024/1024/1024: .2f} GB",
        "total": f"{total/1024/1024/1024: .2f} GB",
        "available": f"{available/1024/1024/1024: .2f} GB",
    }
    body["max"] = f"{max_/1024/1024/1024: .2f} GB" if max_ else "N/A"
    body["percent"] = f"{((used / max_) if max_ else (used / total))*100:.2f}%"

    return MemoryUsage(**body)


def get_memory_max() -> float | None:
    """获取内存限制，容器中有效, 单位为字节"""
    path = Path("/sys/fs/cgroup/memory.max")
    if path.exists():
        return float(path.read_text().strip())
    return None


def format_timedelta(td: timedelta) -> str:
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    formatted = ""
    if days:
        formatted = f"{formatted}{days}d"
    if hours:
        formatted = f"{formatted}{hours}h"
    if minutes:
        formatted = f"{formatted}{minutes}m"
    if seconds:
        formatted = f"{formatted}{seconds}s"

    formatted = f"{days}d{hours}h{minutes}m{seconds}s"
    return formatted


class MemoryUsage(BaseModel):
    """仅限在容器中运行时，max 有效"""

    used: str
    total: str
    available: str
    max_: str = Field(..., alias="max")
    percent: str


class Usage(BaseModel):
    memory: MemoryUsage = Field(default_factory=get_default_memory)


class PingRes(BaseModel):
    message: str = "pong"
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    current: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    run_at_ts: int = run_at_ts
    run_at: str = run_at
    version: str = version
    uptime: str = Field("")
    usage: Usage = Field(default_factory=Usage)

    @validator("uptime", always=True)
    def set_uptime(cls, v, values):
        run_at_ts = values.get("run_at_ts", "")
        current = values.get("timestamp", "")
        uptime = ""
        if run_at_ts and current:
            delta = datetime.fromtimestamp(current) - datetime.fromtimestamp(run_at_ts)
            uptime = format_timedelta(delta)

        return uptime or "N/A"


ping_response_example = {
    "message": "pong",
    "timestamp": 1745137237,
    "current": "2025-04-20 16:20:37",
    "run_at_ts": 1745137209,
    "run_at": "2025-04-20 16:20:09",
    "version": "0.1.13",
    "usage": {
        "memory": {
            "used": "0.97 GB",
            "total": "11.73 GB",
            "available": "10.52 GB",
            "max": " 0.25 GB",
            "percent": "0.08%",
            "test": "121946112.00%",
        }
    },
}


ping_responses: dict[int | str, dict[str, object]] = {
    200: {
        "description": "200 Successful Response",
        "content": {"text/plain": {"example": ping_response_example}},
    }
}
