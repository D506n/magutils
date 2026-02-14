import asyncio
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Callable, Coroutine, Literal
from warnings import warn
from zipfile import ZIP_DEFLATED, ZipFile

import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper

from .basic import BaseAsyncHandler

EXP = Literal['delete', 'compress']
COMPRESSOR = Callable[[Path, AsyncTextIOWrapper], Coroutine[None, None, None]]
FMT = '.zip'
ENCODING = 'utf-8'


async def zip_compressor(file_path: Path, data: AsyncTextIOWrapper):
    zip_path = file_path.parent / (file_path.stem + str(len([
        f for f in file_path.parent.iterdir() if f.suffix == FMT
        ])) + FMT)
    with ZipFile(zip_path, 
                 'a', 
                 compresslevel=9, 
                 compression=ZIP_DEFLATED) as zip_file:
        await asyncio.to_thread(
            zip_file.writestr, file_path.name, await data.read())


class AsyncFileHandler(BaseAsyncHandler):
    def __init__(self, 
                 file_path: Path | str, 
                 max_bytes: int = None, 
                 rotation_by_dt: bool = False, 
                 on_expire: EXP = 'delete', 
                 compressor: COMPRESSOR = None, 
                 buffer_size: int = 500, 
                 *args, **kwargs):
        self._file_path = file_path if isinstance(file_path, Path)\
        else Path(file_path)
        if self._file_path.is_dir():
            self._file_path = self._file_path / 'log.log'
        if not self._file_path.parent.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(*args, **kwargs)
        self.close_buffer = ''
        self.max_bytes = max_bytes
        self.rotation_by_dt = rotation_by_dt
        self.current_log_dt = datetime.now()
        self.on_expire = self._delete_expired_file if on_expire == 'delete'\
            else self._compress_expired_file
        self.compressor = compressor or zip_compressor
        self.buffer: list[str] = []
        self.buffer_size = buffer_size
        self.delayed_flush: asyncio.Task = None
        self.alock = asyncio.Lock()
        self.file: AsyncTextIOWrapper = None

    async def daflush(self):
        await asyncio.sleep(0.01)
        await self.aflush()
        self.delayed_flush = None

    async def aflush(self):
        async with self.alock:
            if self.buffer:
                file = await self.file_open('a')
                await file.write('\n'.join(self.buffer) + '\n')
                await file.flush()
                self.buffer.clear()

    @lru_cache(maxsize=1)
    def _file_path_with_dt(self):
        path = self._file_path.parent / (self._file_path.stem +
        self.current_log_dt.strftime('_%Y_%m_%d') + self._file_path.suffix)
        return path

    @property
    def file_path(self):
        if self.rotation_by_dt:
            return self._file_path_with_dt()
        return self._file_path

    def check_expired(self):
        if self.max_bytes and self.file_path.stat().st_size > self.max_bytes:
            return True
        dt = datetime.now().date()
        if self.rotation_by_dt and self.current_log_dt.date() != dt:
            return True
        return False

    async def _delete_expired_file(self):
        if self.file_path.exists():
            self.file_path.unlink()
        self.file = None

    async def _compress_expired_file(self):
        f = await self.file_open('rb')
        try:
            await self.compressor(self.file_path, f)
        except Exception as e:
            warn(f'Error compressing log file {e}')
        self._file_path_with_dt.cache_clear()
        await self._delete_expired_file()

    async def ajoin(self):
        await super().ajoin()
        await self.file.close()
        with open(self.file_path, 'a', encoding=ENCODING) as f:
            f.write(self.close_buffer)

    @property
    def fparams(self):
        return {
            'file': self.file_path,
            'encoding': ENCODING
        }

    async def file_open(self, mode: str):
        if not self.file or self.file.closed or self.file.mode != mode:
            try:
                await self.file.close()
            except Exception:
                pass
            try:
                self.file = await aiofiles.open(mode=mode, **self.fparams)
            except FileNotFoundError:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                self.file_path.touch(exist_ok=True)
                self.file = await aiofiles.open(mode=mode, **self.fparams)
            # при других ошибках пусть падает, быстрее отловлю
        return self.file

    async def awrite(self, msg):
        if len(self.buffer) < self.buffer_size:
            self.buffer.append(msg)
        else:
            await self.aflush()
            self.buffer.append(msg)
        if self.delayed_flush is None:
            self.delayed_flush = asyncio.create_task(self.daflush())

    async def ahandle(self, record, at_exit=False):
        msg = self.format(record)
        await self.awrite(msg)
        if self.check_expired():
            await self.on_expire()

    def cflush(self):
        if self.buffer:
            with open(mode='a', **self.fparams) as f:
                f.write('\n'.join(self.buffer) + '\n')
            self.buffer.clear()

    def chandle(self, record):
        msg = self.format(record)
        if len(self.buffer) < self.buffer_size:
            self.buffer.append(msg)
        else:
            self.cflush()
            self.buffer.append(msg)