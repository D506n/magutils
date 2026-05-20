import re
from typing import TypedDict

from colorama import Fore


class ColorsDict(TypedDict):
    level: dict[str, str]
    asctime: str
    name: str
    message: str
    reset: str

FMT = '[%(levelname)8s|%(asctime)s|%(name)20s|%(filename)20s:%(lineno)4s] %(message)s' # noqa
TIME = '%Y-%m-%dT%H:%M:%S'
MSEC = '%s:%03d'
COLORS: ColorsDict = {
            'level': {
                'DEBUG': Fore.CYAN, 
                'INFO': Fore.GREEN, 
                'WARNING': Fore.YELLOW, 
                'ERROR': Fore.RED, 
                'CRITICAL': Fore.MAGENTA
            }, 
            'asctime': Fore.BLUE, 
            'name': Fore.YELLOW, 
            'message': Fore.RESET, 
            'reset': Fore.RESET
        }
FORMAT_PARSE_REG = re.compile(r'%\(([A-Za-z]+)\)(\d*)\w')
DEFAULT_FIELDS = {'message', 'funcName', 'name', 'module', 'exc_info', 'msecs', 'levelname', 'process', 'args', 'processName', 'stack_info', 'relativeCreated', 'lineno', 'msg', 'filename', 'levelno', 'created', 'thread', 'threadName', 'taskName', 'asctime', 'exc_text', 'pathname'} # noqa