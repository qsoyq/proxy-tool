from __future__ import annotations

from threading import Lock
from typing import Any, TypeVar, cast

T = TypeVar("T")


def singleton(cls: type[T]) -> type[T]:
    """类装饰器：让类在当前进程内只初始化一个实例。"""

    original_new = cls.__new__
    original_init = cls.__init__
    instance: T | None = None
    initialized = False
    initializing = False
    lock = Lock()

    def singleton_new(singleton_cls: type[T], *args: Any, **kwargs: Any) -> T:
        nonlocal instance

        if instance is None:
            with lock:
                if instance is None:
                    if original_new is object.__new__:
                        instance = cast(T, original_new(singleton_cls))
                    else:
                        instance = cast(T, original_new(singleton_cls, *args, **kwargs))

        return instance

    def singleton_init(self: T, *args: Any, **kwargs: Any) -> None:
        nonlocal initialized, initializing

        if initialized or initializing:
            return

        with lock:
            if initialized or initializing:
                return

            initializing = True
            try:
                original_init(self, *args, **kwargs)
                initialized = True
            finally:
                initializing = False

    cls.__new__ = staticmethod(singleton_new)  # type: ignore[assignment]
    cls.__init__ = singleton_init  # type: ignore[assignment]
    return cls
