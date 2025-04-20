import os
import time
from datetime import datetime
from pathlib import Path

import psutil
from pydantic import BaseModel, Field

run_at_ts = int(time.time())
run_at = datetime.fromtimestamp(run_at_ts).strftime("%Y-%m-%d %H:%M:%S")
version = "0.1.14"


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
    usage: Usage = Field(default_factory=Usage)


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
