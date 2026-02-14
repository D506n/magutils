import copy
from functools import lru_cache, partial
from logging import LogRecord
from typing import Callable
from warnings import warn
from zoneinfo import ZoneInfo

from . import defaults as DEF
from .base import BaseFormatter


class MonocolorFormatter(BaseFormatter):
    def __init__(self, 
                 fmt=DEF.FMT, 
                 datefmt=None, 
                 use_cahce=True, 
                 no_cut=False, 
                 tz: ZoneInfo = None):
        super().__init__(fmt, datefmt, tz=tz)
        self.default_time_format = (DEF.TIME if not datefmt else datefmt)
        self.default_msec_format = DEF.MSEC
        self.use_cache = use_cahce
        self.no_cut = no_cut
        if self.use_cache:
            self.align_substring = lru_cache()(self.align_substring)
        self.fields_mapping = self.parse_format(fmt)
        self.skip_fields = {'asctime', 'message'}

    def align_substring(self, substring, string_width: int):
        if string_width == 0:
            return substring
        if len(str(substring)) > string_width and not self.no_cut:
            return f'...{substring[len(substring) - string_width + 3:]}'
        return f'{substring:^{string_width}}'

    def parse_format(self, format_string):
        variables = DEF.FORMAT_PARSE_REG.findall(format_string)
        result: dict[str, tuple[Callable, Callable]] = {}
        for var, width in variables:
            width = 0 if not width else int(width)
            result[var] = partial(self.align_substring, string_width=width)
        return result

    def format(self, record: LogRecord):
        record = copy.copy(record)
        try:
            for var, align_func in self.fields_mapping.items():
                if var == 'levelname':
                    record.levelname = align_func(record.levelname)
                    continue
                elif var in self.skip_fields:
                    continue
                setattr(record, var, align_func(getattr(record, var)))
        except Exception as e:  # nocov
            warn('Exception occured in logging formatter!')
            print(e)
        else:
            return super().format(record)