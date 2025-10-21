from logging import Formatter, LogRecord
from functools import partial, lru_cache
import re
from typing import Callable

FORMAT_PARSE_REG = re.compile(r'%\(([A-Za-z]+)\)(\d*)\w')

class MonocolorFormatter(Formatter):
    def __init__(self, fmt='[%(levelname)8s|%(asctime)s|%(name)20s|%(filename)20s:%(lineno)3s] %(message)s', datefmt=None, use_cahce=True, no_cut=False):
        super().__init__(fmt, datefmt)
        self.default_time_format = '%Y-%m-%dT%H:%M:%S' if not datefmt else datefmt
        self.default_msec_format = '%s:%03d'
        self.use_cache = use_cahce
        self.no_cut = no_cut
        if self.use_cache:
            self.align_substring = lru_cache()(self.align_substring)
        self.fields_mapping = self.parse_format(fmt)
        self.skip_fields = {'asctime', 'message'}

    def align_substring(self, substring, string_width:int):
        if string_width == 0:
            return substring
        if len(str(substring)) > string_width and not self.no_cut:
            return f'...{substring[len(substring) - string_width+3:]}'
        return f'{substring:^{string_width}}'

    def parse_format(self, format_string):
        variables = FORMAT_PARSE_REG.findall(format_string)
        result:dict[str, tuple[Callable, Callable]] = {}
        for var, width in variables:
            width = 0 if not width else int(width)
            result[var] = partial(self.align_substring, string_width=width)
        return result

    def format(self, record:LogRecord):
        record = LogRecord(record.name, record.levelno, record.pathname, record.lineno, record.msg, record.args, record.exc_info, record.funcName, record.stack_info)
        for var, align_func in self.fields_mapping.items():
            if var == 'levelname':
                record.levelname = align_func(record.levelname)
                continue
            elif var in self.skip_fields:
                continue
            setattr(record, var, align_func(getattr(record, var)))
        return super().format(record)