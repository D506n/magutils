import time
from functools import lru_cache
from logging import Formatter, LogRecord
from warnings import warn

import orjson

from . import defaults as DEF


class JsonFormatter(Formatter):
    def __init__(self, 
                 fmt=DEF.FMT, 
                 datefmt=None, 
                 use_cahce=True, 
                 decode=True):
        super().__init__(fmt, datefmt)
        self.default_time_format = (DEF.TIME if not datefmt else datefmt)
        self.default_msec_format = DEF.MSEC
        self.use_cache = use_cahce
        self.decode = decode
        if self.use_cache:
            self._formatTime = lru_cache()(self._formatTime)
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
        except Exception as e:
            warn('Exception occured in logging formatter!')
            print(e)
        else:
            result = orjson.dumps(json_record)
            if self.decode:
                return result.decode()
            return result

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
        return s