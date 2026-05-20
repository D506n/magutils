import os
from logging import Formatter, LogRecord, basicConfig, getLogger
from logging.handlers import QueueListener
from queue import Queue
from typing import Iterable

from .formatters import (
    ColoredConsoleFormatter,
    JsonFormatter,
    MonocolorFormatter,
)
from .formatters import defaults as fmt_defaults
from .handlers import AsyncConsoleHandler, AsyncFileHandler, BaseAsyncHandler

MP_LISTENER: QueueListener | None = None
MP_QUEUE: Queue[LogRecord] | None = None


def __config(formatter: Formatter,
    level: str | int,
    handlers: Iterable[BaseAsyncHandler],
    force: bool):
    min_level = min(handler.level for handler in handlers)
    basicConfig(level=min_level or level, handlers=handlers, force=force)
    root_logger = getLogger()
    if formatter:
        for handler in root_logger.handlers:
            if isinstance(handler, AsyncConsoleHandler):
                handler.setFormatter(formatter)
            if isinstance(handler, AsyncFileHandler) \
                    and not isinstance(formatter, ColoredConsoleFormatter):
                handler.setFormatter(formatter)
    if force:
        for logger in root_logger.manager.loggerDict.values():
            logger.handlers = root_logger.handlers
            logger.propagate = False


def __handlers_from_env(prefix, level: str | None):
    result = []
    console = os.getenv(f'{prefix}CONSOLE_LOG_LEVEL', 'INFO').upper() in [
        'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    console_json = os.getenv(f'{prefix}CONSOLE_LOG_JSON', 'false').lower() == 'true' # noqa
    file = os.getenv(f'{prefix}LOG_FILE', 'false').lower() == 'true'
    file_json = os.getenv(f'{prefix}LOG_FILE_JSON', 'false').lower() == 'true'
    file_path = os.getenv(f'{prefix}LOG_FILE_PATH', 'data/log.log')
    max_bytes = os.getenv(f'{prefix}LOG_FILE_MAXBYTES')
    log_level = level or os.getenv(f'{prefix}LOG_LEVEL', 'INFO')
    console_log_level = os.getenv(f'{prefix}LOG_CONSOLE_LEVEL', log_level)
    file_log_level = os.getenv(f'{prefix}LOG_FILE_LEVEL', log_level)
    rotation_by_dt = os.getenv(f'{prefix}LOG_FILE_ROTATION_BY_DT', 'false').lower() == 'true' # noqa
    on_expire = os.getenv(f'{prefix}LOG_FILE_ON_EXPIRE', 'delete')
    fmt = os.getenv(f'{prefix}LOG_FORMAT', fmt_defaults.FMT)
    time_fmt = os.getenv(f'{prefix}LOG_TIME_FORMAT', fmt_defaults.TIME)
    use_cache = os.getenv(f'{prefix}LOG_USE_CACHE', 'true').lower() == 'true'
    no_cut = os.getenv(f'{prefix}LOG_NO_CUT', 'false').lower() == 'true'
    mono_formatter = MonocolorFormatter(fmt, time_fmt, use_cache, no_cut)
    colored_formatter = ColoredConsoleFormatter(fmt, time_fmt, use_cache, no_cut=no_cut) # noqa
    if console:
        colors = os.getenv(f'{prefix}LOG_CONSOLE_COLORS', 'true').lower() == 'true' # noqa
        if console_json:
            console_formatter = JsonFormatter(fmt, time_fmt, use_cache)
        elif colors:
            console_formatter = colored_formatter
        else:
            console_formatter = mono_formatter
        ch = AsyncConsoleHandler()
        ch.setFormatter(console_formatter)
        ch.setLevel(console_log_level)
        result.append(ch)
    if file:
        if file_json:
            file_formatter = JsonFormatter(fmt, time_fmt, use_cache)
        else:
            file_formatter = mono_formatter
        fh = AsyncFileHandler(file_path, max_bytes, rotation_by_dt, on_expire)
        fh.setFormatter(file_formatter)
        fh.setLevel(file_log_level)
        result.append(fh)
    if not result:
        ch = AsyncConsoleHandler()
        ch.setFormatter(colored_formatter)
        ch.setLevel(console_log_level)
        result.append(ch)
    return result


def __config_multiprocess(mp_que: Queue[LogRecord]):
    global MP_LISTENER
    global MP_QUEUE
    MP_QUEUE = mp_que
    root = getLogger()
    MP_LISTENER = QueueListener(mp_que, *root.handlers)
    MP_LISTENER.start()


def config_async_logging(
    formatter: ColoredConsoleFormatter | MonocolorFormatter | Formatter = None,
    level: str | int | None = None,
    handlers: Iterable[BaseAsyncHandler] | None = None,
    force: bool = True,
    env_prefix: str = '',
    mp_que: Queue[LogRecord] = None):
    level = level or os.getenv(f'{env_prefix}LOG_LEVEL', 'INFO')
    for handler in handlers or []:
        if handler.level == 0:
            handler.setLevel(level)
    if not handlers:
        handlers = __handlers_from_env(env_prefix, level)
    __config(formatter, level, handlers, force)
    if mp_que:
        __config_multiprocess(mp_que)