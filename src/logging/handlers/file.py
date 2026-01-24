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
                 compressor: COMPRESSOR = None, *args, **kwargs):
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
        async with aiofiles.open(self.file_path, 'w', encoding=ENCODING) as f:
            await f.write('')

    async def _compress_expired_file(self):
        async with aiofiles.open(self.file_path, 'rb', encoding=ENCODING) as f:
            try:
                await self.compressor(self.file_path, f)
            except Exception as e:
                warn(f'Error compressing log file {e}')
        self._file_path_with_dt.cache_clear()
        async with aiofiles.open(self.file_path, 'w', encoding=ENCODING) as f:
            await f.write('')

    async def ajoin(self):
        await super().ajoin()
        with open(self.file_path, 'a', encoding=ENCODING) as f:
            f.write(self.close_buffer)

    async def awrite(self, msg):
        async with aiofiles.open(self.file_path, 'a', encoding=ENCODING) as f:
            await f.write(msg + '\n')

    def write(self, msg):
        self.close_buffer += msg + '\n'

    async def ahandle(self, record, at_exit=False):
        msg = self.format(record)
        if at_exit:
            self.write(msg)
        else:
            await self.awrite(msg)
        if self.check_expired():
            await self.on_expire()