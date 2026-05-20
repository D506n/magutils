from logging import LogRecord
from zoneinfo import ZoneInfo

import orjson

from . import defaults as DEF
from .base import BaseFormatter

SERIALIZABLE = set([str, int, float, type(None), bool])


class JsonFormatter(BaseFormatter):
    def __init__(self, 
                 fmt=DEF.FMT, 
                 datefmt=None, 
                 use_cahce=True, 
                 decode=True,
                 tz: ZoneInfo = None):
        super().__init__(fmt, datefmt, tz=tz)
        self.default_time_format = (DEF.TIME if not datefmt else datefmt)
        self.default_msec_format = DEF.MSEC
        self.use_cache = use_cahce
        self.decode = decode
        self.fields = self.parse_format(fmt)

    def parse_format(self, format_string) -> list[str]:
        return [f[0] for f in DEF.FORMAT_PARSE_REG.findall(format_string)]

    def _serialize_args(self, args: tuple):
        result = []
        for arg in args:
            if type(arg) not in SERIALIZABLE:
                arg = str(arg)
            result.append(arg)
        return tuple(result)

    def format(self, record: LogRecord):
        json_record = {}
        for field in self.fields:
            if field == 'message':
                json_record['args'] = self._serialize_args(record.args)
                print(json_record['args'])
                json_record[field] = record.getMessage()
            elif field == 'asctime':
                json_record[field] = self.formatTime(record)
            else:
                val = getattr(record, field)
                if type(val) not in SERIALIZABLE:
                    val = str(val)
                json_record[field] = val
        json_record['extra'] = {}
        for key, value in [(k, v,) for k, v in record.__dict__.items() 
                                        if k not in DEF.DEFAULT_FIELDS]:
            if type(value) not in SERIALIZABLE:
                value = str(value)
            json_record['extra'][key] = value
        result = orjson.dumps(json_record)
        if self.decode:
            return result.decode()
        return result