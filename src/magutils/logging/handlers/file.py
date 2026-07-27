import asyncio
from datetime import datetime
from functools import cached_property, lru_cache
from pathlib import Path
from threading import Lock
from typing import Callable, Literal, TextIO
from warnings import warn
from zipfile import ZIP_DEFLATED, ZipFile

from ...id import gen_id
from ...time_utils import get_current_time
from .basic import BaseAsyncHandler

EXP = Literal['delete', 'compress']
COMPRESSOR = Callable[[Path, TextIO], None]
FMT = '.zip'
ENCODING = 'utf-8'


def zip_compressor(file_path: Path, data: TextIO):
    path = file_path.parent / (file_path.stem + str(len([
        f for f in file_path.parent.iterdir() if f.suffix == FMT
        ])) + FMT)
    with ZipFile(path, 'a', compresslevel=9, compression=ZIP_DEFLATED) as zipf:
        zipf.writestr(file_path.name, data.read())


class LogFile:
    def __init__(self, 
            path: Path = None, 
            on_expire: EXP = 'delete', 
            compressor: COMPRESSOR = zip_compressor, 
            rotation_by_dt: bool = False,
            current_log_dt: datetime = None,
            max_bytes: int = 0,
            buffer_size: int = 500,
            encoding: str = ENCODING,
            stream: TextIO = None
    ):
        self.mode: Literal['file', 'stream'] = 'file'
        self._path: Path = None
        self.stream: TextIO = None
        self.on_expire = on_expire
        self.exp_act: Callable[[], None] = None
        if stream:
            self.__init_stream(stream)
        elif path:
            self.__init_path(path, on_expire)
        self.compressor = compressor
        self.buffer: list[str] = []
        self.buffer_size = buffer_size
        self.encoding = encoding
        self.rotation_by_dt = rotation_by_dt
        self.current_log_dt = current_log_dt or get_current_time()
        self.max_bytes = max_bytes
        self.alock = asyncio.Lock()
        self.slock = Lock()
        self.delayed_flush = None

    def __init_stream(self, stream: TextIO):
        self.mode = 'stream'
        self.stream = stream
        self.exp_act = self.no_act

    def __init_path(self, path: Path, on_expire: EXP):
        self._path = path
        if self._path.is_dir():
            self._path = self._path / 'log.log'
        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self.exp_act = self.delete if on_expire == 'delete'\
            else self.compress

    @cached_property
    def fparams(self):
        return {
            'file': self.path,
            'encoding': self.encoding
        }

    @property
    def path(self):
        if self.mode == 'stream':
            return Path()
        if self.rotation_by_dt:
            return self.path_with_dt()
        return self._path

    @lru_cache(maxsize=1)
    def path_with_dt(self):
        if self.mode == 'stream':
            return Path()
        path = self._path.parent / (self._path.stem +
            self.current_log_dt.strftime('_%Y_%m_%d') + self._path.suffix)
        return path

    def check_expired(self):
        if self.max_bytes and self.path.stat().st_size > self.max_bytes:
            return True
        dt = get_current_time().date()
        if self.rotation_by_dt and self.current_log_dt.date() != dt:
            return True
        return False

    def delete(self):
        if self.mode == 'stream':
            self.stream.close()
        else:
            if self.stream:
                self.stream.close()
            if self.path.exists():
                self.path.unlink()

    def compress(self):
        f = self.open('rb')
        try:
            self.compressor(self.path, f)
        except Exception as e:
            warn(f'Error compressing log file {e}')
        self.path_with_dt.cache_clear()
        self.delete()

    def no_act(self): pass

    def expire(self):
        with self.slock:
            return self.exp_act()

    def open(self, mode: str):
        if self.mode == 'stream':
            return self.stream
        if not self.stream or self.stream.closed or self.stream.mode != mode:
            fparams = self.fparams
            if 'b' in mode:
                fparams.pop('encoding', None)
            try:
                self.stream.close()
            except Exception:
                pass
            try:
                self.stream = open(mode=mode, **fparams)
            except FileNotFoundError:  # nocov
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.touch(exist_ok=True)
                self.stream = open(mode=mode, **fparams)
            # при других ошибках пусть падает, быстрее отловлю
        return self.stream

    def write(self, row: str):
        if len(self.buffer) >= self.buffer_size:
            self.flush()
            self.buffer.append(row)
        else:
            self.buffer.append(row)

    def flush(self):
        if not self.buffer:
            return
        stream = self.open('a')
        stream.write('\n'.join(self.buffer) + '\n')
        stream.flush()
        self.buffer.clear()

    async def daflush(self):
        await asyncio.sleep(0.01)
        await self.aflush()
        self.delayed_flush = None

    async def aflush(self):
        async with self.alock:
            if self.buffer:
                await asyncio.to_thread(self.flush)

    async def awrite(self, msg):
        if len(self.buffer) < self.buffer_size:
            self.buffer.append(msg)
        else:
            await self.aflush()
            self.buffer.append(msg)
        if self.delayed_flush is None:
            self.delayed_flush = asyncio.create_task(self.daflush())


class AsyncFileHandler(BaseAsyncHandler):
    def __init__(self, 
                 file_path: Path | str, 
                 max_bytes: int = None, 
                 rotation_by_dt: bool = False, 
                 on_expire: EXP = 'delete', 
                 compressor: COMPRESSOR = None, 
                 buffer_size: int = 500, 
                 file: LogFile = None,
                 *args, **kwargs):
        _file_path = file_path if isinstance(file_path, Path)\
            else Path(file_path)
        super().__init__(*args, **kwargs)
        self.delayed_flush: asyncio.Task = None
        self.alock = asyncio.Lock()
        self.file = file or LogFile(
            _file_path, 
            on_expire, 
            compressor, 
            rotation_by_dt, 
            get_current_time(), 
            max_bytes,
            buffer_size
        )

    async def ahandle(self, record, at_exit=False):
        if e := self.extract_exception(record):
            _id = gen_id()
            msgs = self.format_exception(record, e, _id)
            if isinstance(msgs, list):
                record.call_stack = msgs
                msg = self.format(record)
                await self.file.awrite(msg)
            else:
                record.msg = f'<{_id}>{record.msg}'
                msg = self.format(record)
                await self.file.awrite(msg)
                for msg in msgs:
                    await self.file.awrite(msg)
        else:
            msg = self.format(record)
            await self.file.awrite(msg)
        if self.file.check_expired():
            await asyncio.to_thread(self.file.expire)

    def cflush(self):
        self.file.flush()

    def chandle(self, record):
        msg = self.format(record)
        self.file.write(msg)