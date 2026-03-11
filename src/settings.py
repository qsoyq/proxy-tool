import logging
import os
import time
import tomllib
from pathlib import Path
from typing import Tuple, Type

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from typer_utils.utils import get_project_version
from utils.basic import get_date_string_for_shanghai

run_at_ts = int(time.time())
run_at = get_date_string_for_shanghai(run_at_ts)
version = str(get_project_version())


class MCPSettings(BaseSettings):  # type:ignore
    mcp_name: str = "proxy-tool-mcp"
    mcp_description: str = "proxy tool mcp"


class AppSettings(BaseSettings):
    mcp: MCPSettings = MCPSettings()

    api_prefix: str = "/api"
    log_level: int = logging.INFO
    basic_auth_user: str = "root"
    basic_auth_passwd: str = "example"

    gc_trigger_memory_percent_limit: float = 80
    gc_trigger_memory_percent_interval: int = 30

    cloud_scraper_verify: bool = True

    # calander
    ## vlrgg
    ics_fetch_vlrgg_match_time_semaphore: int = 15

    # rss
    ## douyin
    rss_douyin_user_semaphore: int = 5
    rss_douyin_user_feeds_cache_time: int = 1800
    rss_douyin_user_auto_fetch_timeout: float = 60
    rss_douyin_user_auto_fetch_start_wait: float = 30
    rss_douyin_user_auto_fetch_enable: bool = False
    rss_douyin_user_auto_fetch_wait: int = 600
    rss_douyin_user_auto_fetch_once_wait: int = 10
    rss_douyin_user_history_storage: str = "~/.proxy-tool/rss.douyin.user.history"
    rss_douyin_user_headless: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        toml_file=os.getenv("CONFIG_FILE", ".settings.toml"),
        extra="ignore",  # 忽略 TOML 文件中的额外字段
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """自定义配置源，优先级：初始化参数 > TOML 文件 > 环境变量"""
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls),
            env_settings,
        )

    @classmethod
    def from_toml(cls, toml_path: str | Path) -> "AppSettings":
        if isinstance(toml_path, str):
            toml_path = Path(toml_path).resolve()
        if not toml_path.exists() or not toml_path.is_file():
            raise FileNotFoundError(f"配置文件不存在或不是文件: {toml_path}")
        try:
            return cls.model_validate(tomllib.loads(toml_path.read_text(encoding="utf-8")))
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"配置文件解析失败: {e}")

    @classmethod
    def update_from_toml(cls, app_config: "AppSettings", toml_path: str | Path) -> None:
        """从 TOML 文件更新配置对象（直接修改传入的对象）"""
        new_config = cls.from_toml(toml_path)

        for field_name in cls.model_fields.keys():
            setattr(app_config, field_name, getattr(new_config, field_name))


settings = AppSettings()


def get_settings() -> AppSettings:
    return settings
