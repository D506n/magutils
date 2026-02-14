from datetime import datetime
from logging import Formatter
from zoneinfo import ZoneInfo

from src.utils.time_utils import format_time, get_tz

from . import defaults as DEF


class BaseFormatter(Formatter):
    def __init__(self, 
                 fmt=None, 
                 datefmt=None, 
                 style="%",
                 validate=True, 
                 *, 
                 defaults=None,
                 tz: ZoneInfo = None):
        self.tz = tz or get_tz()
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)

    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created, self.tz)
        s = format_time(ct, datefmt or DEF.TIME)
        s = self.default_msec_format % (s, record.msecs)
        return s