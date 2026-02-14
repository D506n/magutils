from logging import LogRecord
from warnings import warn
from zoneinfo import ZoneInfo

import orjson

from . import defaults as DEF
from .base import BaseFormatter


class JsonFormatter(BaseFormatter):
    def __init__(self, 
                 fmt=DEF.FMT, 
                 datefmt=None, 
                 decode=True,
                 tz: ZoneInfo = None):
        super().__init__(fmt, datefmt, tz=tz)
        self.default_time_format = (DEF.TIME if not datefmt else datefmt)
        self.default_msec_format = DEF.MSEC
        self.decode = decode
        self.fields = self.parse_format(fmt)

    def parse_format(self, format_string) -> list[str]:
        return [f[0] for f in DEF.FORMAT_PARSE_REG.findall(format_string)]

    def format(self, record: LogRecord):
        try:
            json_record = {}
            for field in self.fields:
                if field == 'message':
                    json_record[field] = record.getMessage()
                    json_record['args'] = record.args
                elif field == 'asctime':
                    json_record[field] = self.formatTime(record)
                else:
                    json_record[field] = getattr(record, field)
            json_record['extra'] = {}
            for key, value in [(k, v,) for k, v in record.__dict__.items() 
                                            if k not in DEF.DEFAULT_FIELDS]:
                json_record['extra'][key] = value
        except Exception as e:  # nocov
            warn('Exception occured in logging formatter!')
            print(e)
        else:
            result = orjson.dumps(json_record)
            if self.decode:
                return result.decode()
            return result