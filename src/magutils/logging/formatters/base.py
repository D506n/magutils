from copy import copy
from datetime import datetime
from logging import Formatter, LogRecord
from traceback import extract_tb
from typing import Any, Optional
from zoneinfo import ZoneInfo

from ...time_utils import format_time, get_tz
from . import defaults as DEF


class BaseFormatter(Formatter):
    def __init__(self, 
                 fmt=None, 
                 datefmt=None, 
                 style="%",
                 validate=True, 
                 *, 
                 defaults=None,
                 tz: Optional[ZoneInfo] = None):
        self.tz = tz or get_tz()
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)

    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created, self.tz)
        s = format_time(ct, datefmt or DEF.TIME)
        s = self.default_msec_format % (s, record.msecs)
        return s

    def format_exception(self, 
            rec: LogRecord, 
            e: Exception, 
            trace_id: str, 
            limit: int = 25):
        rows = extract_tb(e.__traceback__, limit=limit * -1)
        for r in rows:
            newr = copy(rec)
            newr.args = tuple()
            newr.msg = (f'<{trace_id}>File: "{r.filename}", '
                                f'line: {r.lineno}, in: {r.line}')
            yield self.format(newr)

    def format(self, record):
        rec = super().format(record)
        if hasattr(record, 'log_ctx'):
            ctx: dict[str, Any] = getattr(record, 'log_ctx').copy()
            if 'trace_id' in ctx.keys():
                rec = f'[trace_id: {ctx.pop('trace_id')}]' + rec
            if ctx:
                rec = (
                    f"{rec} | "
                    f"ctx: {', '.join([f'{k} = {v}' for k, v in ctx.items()])}"
                )
        return rec