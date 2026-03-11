import logging

import click


class MixdCloudPilotStreamHandler(logging.StreamHandler):
    """项目自有的 stream handler，用于避免重复挂载。"""


class ColorFormatter(logging.Formatter):
    _format = "%(asctime)s.%(msecs)03d %(levelname)s %(message)s"
    _datefmt = "%Y-%m-%d %H:%M:%S"

    log_colors: dict[int, list[tuple[str, str]]] = {
        logging.DEBUG: [
            ("%(levelname)s", "cyan"),
        ],
        logging.INFO: [
            ("%(levelname)s", "green"),
        ],
        logging.WARNING: [
            ("%(levelname)s", "yellow"),
            ("%(message)s", "yellow"),
        ],
        logging.ERROR: [
            ("%(levelname)s", "red"),
            ("%(message)s", "red"),
        ],
        logging.CRITICAL: [
            ("%(levelname)s", "bright_red"),
            ("%(message)s", "bright_red"),
        ],
    }

    def format(self, record: logging.LogRecord):
        log_fmt = self._format

        color_handlers: list[tuple[str, str]] = self.log_colors.get(record.levelno, [])
        for text, color in color_handlers:
            log_fmt = log_fmt.replace(text, click.style(str(text), fg=color))

        formatter = logging.Formatter(log_fmt, datefmt=self._datefmt)
        return formatter.format(record)


def _ensure_stream_handler(
    logger: logging.Logger,
    formatter: logging.Formatter,
    *,
    propagate: bool = True,
) -> None:
    logger.propagate = propagate

    for handler in logger.handlers:
        if isinstance(handler, MixdCloudPilotStreamHandler):
            handler.setFormatter(formatter)
            return

    handler = MixdCloudPilotStreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def init_logger(log_level: int) -> None:
    color_formatter = ColorFormatter()

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    _ensure_stream_handler(root_logger, color_formatter)

    logger = logging.getLogger("http.access")
    logger.setLevel(log_level)
    _ensure_stream_handler(logger, color_formatter, propagate=False)
