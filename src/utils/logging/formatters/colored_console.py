import time
from functools import lru_cache, partial
from logging import Formatter, LogRecord
from typing import Callable
from warnings import warn

from colorama import Fore

from . import defaults as DEF


class ColoredConsoleFormatter(Formatter):
    def __init__(self, 
                 fmt=DEF.FMT, # noqa
                 datefmt=None, 
                 use_cache=True, 
                 custom_colors=None, 
                 no_cut=False):
        super().__init__(fmt, datefmt)
        self.default_time_format = (DEF.TIME if not datefmt else datefmt)
        self.default_msec_format = DEF.MSEC
        self.use_cache = use_cache
        self.colors = DEF.COLORS
        self.no_cut = no_cut
        if isinstance(custom_colors, dict):
            self.colors.update(custom_colors)
        if self.use_cache:
            self.get_level_color = lru_cache()(self.get_level_color)
            self._formatTime = lru_cache()(self._formatTime)
            self.align_substring = lru_cache()(self.align_substring)
            self.color_substring = lru_cache()(self.color_substring)
        self.fields_mapping = self.parse_format(fmt)
        self.skip_fields = {'asctime', 'message'}

    def get_level_color(self, level):
        return self.colors['level'].get(level, Fore.RESET)

    def color_substring(self, substring, color):
        return color + substring + Fore.RESET

    def align_substring(self, substring, string_width: int):
        if not isinstance(substring, str):
            substring = str(substring)
        if string_width == 0:
            return substring
        if len(substring) > string_width and not self.no_cut:
            return f'...{substring[len(substring) - string_width + 3:]}'
        return f'{substring:^{string_width}}'

    def parse_format(self, format_string):
        variables = DEF.FORMAT_PARSE_REG.findall(format_string)
        result: dict[str, tuple[Callable, Callable]] = {}
        for var, width in variables:
            width = 0 if not width else int(width)
            result[var] = (
                partial(
                    self.color_substring, 
                    color=self.colors.get(var, Fore.RESET)), 
                partial(
                    self.align_substring, 
                    string_width=width))
        return result

    def format(self, record: LogRecord):
        record = LogRecord(
            record.name, 
            record.levelno, 
            record.pathname, 
            record.lineno, 
            record.msg, 
            record.args, 
            record.exc_info, 
            record.funcName, 
            record.stack_info)
        try:
            for var, (color_func, align_func) in self.fields_mapping.items():
                if var == 'levelname':
                    level = record.levelname
                    record.levelname = align_func(record.levelname)
                    record.levelname = (self.get_level_color(level) + 
                                                        record.levelname + 
                                                        Fore.RESET)
                    continue
                elif var in self.skip_fields:
                    continue
                setattr(record, var, align_func(getattr(record, var)))
                setattr(record, var, color_func(getattr(record, var)))
        except Exception as e:
            warn('Exception occured in logging formatter!')
            print(e)
        return super().format(record)

    def formatMessage(self, record):
        return (self.colors['message'] + 
                     super().formatMessage(record) + 
                     Fore.RESET)

    def formatTime(self, record: LogRecord, datefmt=None):
        dt = self._formatTime(record.created, datefmt, record.msecs)
        return dt

    def _formatTime(self, created, datefmt, msecs):
        ct = time.localtime(created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime(self.default_time_format, ct)
            if self.default_msec_format:
                s = self.default_msec_format % (s, msecs)
        s = self.fields_mapping['asctime'][1](s)
        s = self.fields_mapping['asctime'][0](s)
        return s