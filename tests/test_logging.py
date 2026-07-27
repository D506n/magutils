from src.magutils.logging.formatters import MonocolorFormatter, ColoredConsoleFormatter, JsonFormatter
from src.magutils.logging.formatters.base import BaseFormatter
from colorama import Fore
import pytest
from logging import getLogger, LogRecord
import re
from functools import partial
import orjson
from contextlib import contextmanager
from src.magutils.logging.handlers import BaseAsyncHandler, AsyncConsoleHandler, AsyncFileHandler, RawQueueHandler
from src.magutils.logging.handlers.file import LogFile, zip_compressor
from typing import TypeVar, Generator
from unittest.mock import AsyncMock, Mock
import asyncio as aio
from io import StringIO
from queue import Queue
import pickle
from pathlib import Path
from zipfile import ZipFile


def log_record(kw: dict = None):
    if not kw:
        kw = {}
    kwargs = {
        "name": "test",
        "level": 40,
        'fn': __file__,
        'lno': 123,
        'sinfo': '',
        "exc_info": None,
        "msg": "test %s",
        "args": ("test_arg1",)
    }
    kwargs.update(kw)
    rec = getLogger().makeRecord(**kwargs)
    return rec

def calc_time(ns: int):
    created = ns / 1e9
    msecs = (ns % 1_000_000_000) // 1_000_000 + 0.0
    if msecs == 999.0 and int(ns) != ns // 1_000_000_000:
            # ns -> sec conversion can round up, e.g:
            # 1_677_903_920_999_999_900 ns --> 1_677_903_921.0 sec
        msecs = 0.0
    return created, msecs

def error_func(arg, arg2):
    if arg2 > 0:
        return error_func(arg, arg2-1)
    return arg/arg2

T = TypeVar('T', bound=BaseAsyncHandler)

@contextmanager
def init_handler(hndlr: type[T], **kw):
    handler = hndlr(**kw)
    yield handler
    if not hasattr(handler, 'closing_event'):
        return
    if not handler.closing_event.is_set():
        handler.close()

msg_reg = re.compile(r'<[0-9A-Za-z]+>File:\s"[\/A-Za-z0-9_\.]+",\sline:\s\d+,\sin:\s.+')
msg_id_reg = re.compile(r'<[0-9A-Za-z]+>')

globfmt_color = ColoredConsoleFormatter()

class TestBaseFormatter:
    @pytest.mark.parametrize(
        'ct, expect',
        [
            (1784935755253500279, '2026-07-24T23:29:15,253',),
            (1784935838025190196, '2026-07-24T23:30:38,025',),
            (1784935857917736172, '2026-07-24T23:30:57,917',)
        ]
    )
    def test_format_time(self, ct, expect):
        record = log_record()
        fmt = BaseFormatter()
        rec_cr, msecs = calc_time(ct)
        record.created = rec_cr
        record.msecs = msecs
        t = fmt.formatTime(record)
        assert t == expect

    def test_format_exception(self):
        try:
            error_func(1, 10)
        except Exception as e:
            record = log_record({'msg': e, "args": tuple()})
            fmt = BaseFormatter()
            gen = fmt.format_exception(record, e, '123')
            i = 0
            for row in gen:
                i += 1
                assert msg_reg.search(row) is not None
            assert i == 12
            gen = fmt.format_exception(record, e, "123", 3)
            rows = list(gen)
            assert len(rows) == 3
            f1 = 'return error_func(arg, arg2-1)'
            f2 = 'return arg/arg2'
            assert f1 in rows[0] and f1 in rows[1]
            assert f2 in rows[2]

class TestColoredConsoleFormatter:
    def test_get_color_default(self):
        fmt = ColoredConsoleFormatter()
        assert fmt.get_level_color('DEBUG') == Fore.CYAN
        assert fmt.get_level_color('INFO') == Fore.GREEN
        assert fmt.get_level_color('WARNING') == Fore.YELLOW
        assert fmt.get_level_color('ERROR') == Fore.RED
        assert fmt.get_level_color('CRITICAL') == Fore.MAGENTA
        assert fmt.get_level_color('NEW') == Fore.RESET

    def test_get_color_custom(self):
        fmt = ColoredConsoleFormatter(custom_colors={"level": {'DEBUG': Fore.BLACK}})
        assert fmt.get_level_color('DEBUG') == Fore.BLACK
        assert fmt.get_level_color('INFO') == Fore.GREEN
        assert fmt.get_level_color('NEW') == Fore.RESET

    def test_color_substring(self):
        fmt = ColoredConsoleFormatter()
        assert fmt.color_substring('test', Fore.RED) == f'{Fore.RED}test{Fore.RESET}'

    @pytest.mark.parametrize(
            "substring, width, expect",
            [
                (123, 3, '123'),
                ("123", 5, ' 123 '),
                ('123', 6, ' 123  '),
                ('long string', 6, '...ing')
            ]
    )
    def test_align_substring(self, substring, width, expect):
        fmt = ColoredConsoleFormatter()
        assert fmt.align_substring(substring, width) == expect

    @pytest.mark.parametrize(
            'fmt_string, string, expect_len, expect',
            [
                (
                    '[%(levelname)8s|%(asctime)s|%(name)20s|%(filename)20s:%(lineno)4s] %(message)s', 
                    'test', 
                    6, 
                    {
                        'levelname': (partial(globfmt_color.color_substring, color=globfmt_color.get_level_color('test')), partial(globfmt_color.align_substring, string_width=8),),
                        'asctime': (partial(globfmt_color.color_substring, color='\x1b[34m'), partial(globfmt_color.align_substring, string_width=0),),
                        'name': (partial(globfmt_color.color_substring, color='\x1b[33m'), partial(globfmt_color.align_substring, string_width=20),),
                        'filename': (partial(globfmt_color.color_substring, color='\x1b[39m'), partial(globfmt_color.align_substring, string_width=20),),
                        'lineno': (partial(globfmt_color.color_substring, color='\x1b[39m'), partial(globfmt_color.align_substring, string_width=4),),
                        "message": (partial(globfmt_color.color_substring, color='\x1b[39m'), partial(globfmt_color.align_substring, string_width=0),),
                    }
                ),
                (
                    '%(levelname)12s %(asctime)10s',
                    'test',
                    2,
                    {
                        'levelname': (partial(globfmt_color.color_substring, color=globfmt_color.get_level_color('test')), partial(globfmt_color.align_substring, string_width=12),),
                        'asctime': (partial(globfmt_color.color_substring, color='\x1b[34m'), partial(globfmt_color.align_substring, string_width=10),),
                    }
                )
            ]
    )
    def test_parse_format(self, fmt_string, string, expect_len, expect):
        fmt = ColoredConsoleFormatter()
        result = fmt.parse_format(fmt_string)
        assert len(result) == expect_len
        for k, v in result.items():
            coloring = v[0]
            aligning = v[1]
            print(coloring(string))
            print(aligning(string))
            assert coloring(string) == expect[k][0](string)
            assert aligning(string) == expect[k][1](string)

    def test_format(self):
        fmt = ColoredConsoleFormatter()
        time = 1784935755253500279
        expect = '\x1b[39m[\x1b[31m ERROR  \x1b[39m|\x1b[34m2026-07-24T23:29:15:253\x1b[39m|\x1b[33m        test        \x1b[39m|\x1b[39m  test_logging.py   \x1b[39m:\x1b[39m123 \x1b[39m] test test_arg1\x1b[39m'
        record = log_record()
        created, msecs = calc_time(time)
        record.created = created
        record.msecs = msecs
        rec_msg = record.msg
        rec_levname = record.levelname
        result = fmt.format(record)
        assert rec_msg == record.msg
        assert rec_levname == record.levelname
        assert result == expect

class TestMonoColorFormatter:
    @pytest.mark.parametrize(
            "substring, widht, expect",
            [
                ('test', 8, '  test  '),
                ('test', 10, '   test   '),
                ('test', 0, 'test'),
                ('test', 13, '    test     '),
                ("test long string", 6, '...ing')
            ]
    )
    def test_align_substring(self, substring, widht, expect):
        fmt = MonocolorFormatter()
        assert fmt.align_substring(substring, widht) == expect

    @pytest.mark.parametrize(
        "fmt_string, string, expect_len, expect",
        [
            (
                '[%(levelname)8s|%(asctime)s|%(name)20s|%(filename)20s:%(lineno)4s] %(message)s', 
                'test', 
                6, 
                {
                    'levelname': partial(globfmt_color.align_substring, string_width=8),
                    'asctime': partial(globfmt_color.align_substring, string_width=0),
                    'name': partial(globfmt_color.align_substring, string_width=20),
                    'filename': partial(globfmt_color.align_substring, string_width=20),
                    'lineno': partial(globfmt_color.align_substring, string_width=4),
                    "message": partial(globfmt_color.align_substring, string_width=0),
                }
            ),
            (
                '%(levelname)12s %(asctime)10s',
                'test',
                2,
                {
                    'levelname': partial(globfmt_color.align_substring, string_width=12),
                    'asctime': partial(globfmt_color.align_substring, string_width=10),
                }
            )
        ]
    )
    def test_parse_format(self, fmt_string, string, expect_len, expect):
        fmt = MonocolorFormatter()
        result = fmt.parse_format(fmt_string)
        assert len(result) == expect_len
        for k, v in result.items():
            assert v(string) == expect[k](string)

    def test_format(self):
        fmt = MonocolorFormatter()
        time = 1784935755253500279
        expect = '[ ERROR  |2026-07-24T23:29:15:253|        test        |  test_logging.py   :123 ] test test_arg1'
        record = log_record()
        created, msecs = calc_time(time)
        record.created = created
        record.msecs = msecs
        rec_msg = record.msg
        rec_levname = record.levelname
        result = fmt.format(record)
        assert rec_msg == record.msg
        assert rec_levname == record.levelname
        assert result == expect


class TestJsonFormatter:
    @pytest.mark.parametrize(
        "fmt_string, expect",
        [
            (
                '{"levelname": "%(levelname)s", "asctime": "%(asctime)s"}',
                ['levelname', 'asctime']
            ),
            (
                '[%(levelname)8s|%(asctime)s|%(name)20s|%(filename)20s:%(lineno)4s] %(message)s',
                ['levelname', 'asctime', 'name', 'filename', 'lineno', 'message']
            ),
        ]
    )
    def test_parse_format(self, fmt_string, expect):
        fmt = JsonFormatter()
        result = fmt.parse_format(fmt_string)
        assert set(expect) == set(result)

    @pytest.mark.parametrize(
            "kw",
            [
                {'decode': True},
                {'decode': False},
            ]
    )
    def test_format_base(self, kw):
        fmt = JsonFormatter(**kw)
        record = log_record()
        time = 1784935755253500279
        expect = {"levelname":"ERROR","asctime":"2026-07-24T23:29:15:253","name":"test","filename":"test_logging.py","lineno":123,"args":["test_arg1"],"message":"test test_arg1","extra":{}}
        record = log_record()
        created, msecs = calc_time(time)
        record.created = created
        record.msecs = msecs
        rec_msg = record.msg
        rec_levname = record.levelname
        result = fmt.format(record)
        assert rec_msg == record.msg
        assert rec_levname == record.levelname
        assert orjson.loads(result) == expect

    def test_format_cornercase(self):
        # Несериализуемые аргументы оборачиваются в строку
        class Unserializable():
            def __str__(self):
                return 'test'
        unsrlz = Unserializable()
        fmt = JsonFormatter()
        record = log_record({'msg': "%s", 'args': (unsrlz,)})
        msg = fmt.format(record)
        assert orjson.loads(msg)['message'] == 'test'

        # Несериализуемые экстра поля тоже оборачиваются в строку
        record = log_record({'msg': 'test', "args": tuple(), 'extra': {'test': unsrlz}})
        msg = fmt.format(record)
        assert orjson.loads(msg)['extra']['test'] == 'test'

    def test_format_exception(self):

        try:
            error_func(1, 10)
        except Exception as e:
            record = log_record({'msg': e, "args": tuple()})
            fmt = JsonFormatter()
            trace = fmt.format_exception(record, e, '123')
            i = 0
            for row in trace:
                i += 1
                assert msg_reg.search(row) is not None
            assert i == 12
            trace = fmt.format_exception(record, e, "123", 3)
            assert len(trace) == 3
            f1 = 'return error_func(arg, arg2-1)'
            f2 = 'return arg/arg2'
            assert f1 in trace[0] and f1 in trace[1]
            assert f2 in trace[2]


class TestBaseHandler:
    @pytest.mark.asyncio
    async def test_emit_normal(self):
        with init_handler(BaseAsyncHandler) as handler:
            assert handler.queue.qsize() == 0
            handler.emit(log_record())
            assert handler.bg_task is not None
            assert handler.queue.qsize() == 1

    def test_emit_corner(self):
        # Если обработчик закрыт, то в очередь ничего не добавится
        with init_handler(BaseAsyncHandler) as handler:
            pass
        handler.emit(log_record())
        assert handler.queue.qsize() == 0
        handler.close()  # повторное закрытие не вызывает никаких ошибок, просто выход

        # Если не запущен луп, обработчик не падает, а откладывает задачу в очередь
        with init_handler(BaseAsyncHandler) as handler:
            handler.emit(log_record())
            assert handler.queue.qsize() == 1
            assert handler.bg_task is None

    @pytest.mark.asyncio
    async def test_read_queue_processes_record(self):
        with init_handler(BaseAsyncHandler) as handler:
            ahandle_mock = AsyncMock()
            handler.ahandle = ahandle_mock

            record = log_record()
            handler.emit(record)
            await aio.sleep(0.1)

            ahandle_mock.assert_awaited_once_with(record, at_exit=False)
            assert handler.queue.qsize() == 0
        await aio.sleep(0.6)
        assert handler.bg_task.done()

    def test_extract_exception(self):
        with init_handler(BaseAsyncHandler) as handler:
            try:
                1/0
            except Exception as e:
                record = log_record({'msg': e, 'args': tuple()})
                exception = handler.extract_exception(record)
                assert exception is e

                record = log_record({'msg': '%s', 'args': (e,)})
                exception = handler.extract_exception(record)
                assert exception is e

    def test_format_exception(self):
        # Обычный форматировщик
        with init_handler(BaseAsyncHandler) as handler:
            handler.setFormatter(ColoredConsoleFormatter())
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, 'args': tuple()})
                tid = '123'
                rows = handler.format_exception(record, e, tid)
                assert not isinstance(rows, list)
                for row in rows:
                    assert msg_reg.search(row)

        # Json форматировщик
        with init_handler(BaseAsyncHandler) as handler:
            handler.setFormatter(JsonFormatter())
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, 'args': tuple()})
                tid = '123'
                rows = handler.format_exception(record, e, tid)
                assert isinstance(rows, list)
                for row in rows:
                    assert msg_reg.search(row)

        # Без форматировщика/с неподходящим форматировщиком
        # и ограничением глубины
        with init_handler(BaseAsyncHandler) as handler:
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, 'args': tuple()})
                tid = '123'
                rows = handler.format_exception(record, e, tid, 2)
                assert not isinstance(rows, list)
                assert len(list(rows)) == 2

    def test_close_with_buffer(self):
        stdout = StringIO()

        mock_cflush = Mock()
        with init_handler(BaseAsyncHandler) as handler:
            handler.buffer = stdout  # в потомках и так переопределяется
            handler.cflush = mock_cflush
        mock_cflush.assert_called_once()


class TestConsoleHandler:
    @pytest.mark.asyncio
    async def test_ahandle(self):
        stdout = StringIO()

        with init_handler(AsyncConsoleHandler, buffer_size=20, stdout=stdout) as handler:
            handler.setFormatter(MonocolorFormatter())

            # тест обработки обычной ошибки
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, "args": tuple()})
                await handler.ahandle(record, False)
                await aio.sleep(0.1)
                lines = stdout.getvalue().strip().split('\n')
                assert msg_id_reg.search(lines[0])
                for line in lines[1:]:
                    assert msg_reg.search(line)
                assert len(lines) == 6
                stdout.truncate(0)
                stdout.seek(0)

            # тест обработки логов с переполнением буфера
            for i in range(30):
                record = log_record({'msg': '%s', 'args': (i,)})
                await handler.ahandle(record, False)
            await aio.sleep(0.1)
            lines = stdout.getvalue().strip().split('\n')
            assert len(lines) == 30
            for i, line in enumerate(lines):
                assert line.endswith(f'|        test        |  test_logging.py   :123 ] {i}')
            stdout.truncate(0)
            stdout.seek(0)

            # тест обработки ошибки, но с json форматировщиком
            handler.setFormatter(JsonFormatter())
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, "args": tuple()})
                await handler.ahandle(record, False)
                await aio.sleep(0.1)
                lines = stdout.getvalue().strip().split('\n')
                assert len(lines) == 1
                row = orjson.loads(lines[0])
                print(row)
                assert len(row['extra']['call_stack']) == 5
                for line in row['extra']['call_stack']:
                    assert msg_reg.search(line)
            stdout.truncate(0)
            stdout.seek(0)

    def test_chandle(self):
        stdout = StringIO()

        with init_handler(AsyncConsoleHandler, buffer_size=20, stdout=stdout) as handler:
            handler.setFormatter(MonocolorFormatter())

            # тест обработки обычной ошибки
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, "args": tuple()})
                handler.chandle(record)
                handler.cflush()
                lines = stdout.getvalue().strip().split('\n')
                assert msg_id_reg.search(lines[0])
                for line in lines[1:]:
                    assert msg_reg.search(line)
                assert len(lines) == 6
                stdout.truncate(0)
                stdout.seek(0)

            # тест обработки логов с переполнением буфера
            for i in range(30):
                record = log_record({'msg': '%s', 'args': (i,)})
                handler.chandle(record)
            handler.cflush()
            lines = stdout.getvalue().strip().split('\n')
            assert len(lines) == 30
            for i, line in enumerate(lines):
                assert line.endswith(f'|        test        |  test_logging.py   :123 ] {i}')
            stdout.truncate(0)
            stdout.seek(0)

            # тест обработки ошибки, но с json форматировщиком
            handler.setFormatter(JsonFormatter())
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, "args": tuple()})
                handler.chandle(record)
                handler.cflush()
                lines = stdout.getvalue().strip().split('\n')
                assert len(lines) == 1
                row = orjson.loads(lines[0])
                assert len(row['extra']['call_stack']) == 5
                for line in row['extra']['call_stack']:
                    assert msg_reg.search(line)
            stdout.truncate(0)
            stdout.seek(0)


class TestRawQueueHandler:
    def test_emit(self):
        queue = Queue()
        with init_handler(RawQueueHandler, queue=queue) as handler:
            # лог с исключением
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, "args": tuple()})
                handler.emit(record)
                raw = queue.get()
                queue.task_done()
                assert isinstance(raw, bytes)
                data = pickle.loads(raw)
                assert isinstance(data, LogRecord)
                assert isinstance(data.call_stack, list)

            # лог с неупаковываемым полем
            class NotPicklable:
                def __str__(self):
                    return 'test'

                def __getstate__(self):
                    raise AttributeError('Not picklable')

            unpicklable = NotPicklable()
            record = log_record({'msg': 'test %s', 'args': (unpicklable,)})
            handler.emit(record)
            raw = queue.get()
            queue.task_done()
            assert isinstance(raw, bytes)
            data = pickle.loads(raw)
            assert isinstance(data, LogRecord)
            assert data.getMessage() == 'test test'


class TestAsyncFileHandler:
    def test_init_default(self, tmp_path):
        """Создаётся с LogFile по умолчанию."""
        with init_handler(AsyncFileHandler, file_path=tmp_path / 'test.log') as handler:
            assert isinstance(handler.file, LogFile)
            assert handler.file._path == tmp_path / 'test.log'

    def test_init_custom_file(self, tmp_path):
        """Переданный file=LogFile(...) используется."""
        logfile = LogFile(path=tmp_path / 'custom.log')
        with init_handler(AsyncFileHandler, file_path=tmp_path / 'ignored.log', file=logfile) as handler:
            assert handler.file is logfile
            assert handler.file._path == tmp_path / 'custom.log'

    @pytest.mark.asyncio
    async def test_ahandle_normal(self, tmp_path):
        """Обычный лог → file.awrite."""
        path = tmp_path / 'test.log'
        with init_handler(AsyncFileHandler, file_path=path) as handler:
            handler.setFormatter(MonocolorFormatter())
            record = log_record()
            await handler.ahandle(record, at_exit=False)
            # ждём отложенный flush
            await aio.sleep(0.05)
            content = path.read_text()
            assert 'test test_arg1' in content

    @pytest.mark.asyncio
    async def test_ahandle_with_exception(self, tmp_path):
        """Лог с исключением → пишется стектрейс."""
        path = tmp_path / 'test.log'
        with init_handler(AsyncFileHandler, file_path=path) as handler:
            handler.setFormatter(MonocolorFormatter())
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, "args": tuple()})
                await handler.ahandle(record, at_exit=False)
                await aio.sleep(0.05)
                content = path.read_text()
                assert msg_id_reg.search(content)
                assert msg_reg.search(content)

    @pytest.mark.asyncio
    async def test_ahandle_with_exception_json(self, tmp_path):
        """Лог с исключением и JsonFormatter."""
        path = tmp_path / 'test.log'
        with init_handler(AsyncFileHandler, file_path=path) as handler:
            handler.setFormatter(JsonFormatter())
            try:
                error_func(10, 3)
            except Exception as e:
                record = log_record({'msg': e, "args": tuple()})
                await handler.ahandle(record, False)
                await aio.sleep(0.05)
                content = path.read_text()
                row = orjson.loads(content.strip())
                assert len(row['extra']['call_stack']) == 5

    @pytest.mark.asyncio
    async def test_ahandle_expired(self, tmp_path):
        """check_expired() → вызывается expire."""
        path = tmp_path / 'test.log'
        path.write_text('x' * 100)
        with init_handler(AsyncFileHandler, file_path=path, max_bytes=50) as handler:
            handler.setFormatter(MonocolorFormatter())
            record = log_record()
            mock_expire = Mock()
            handler.file.expire = mock_expire
            await handler.ahandle(record, at_exit=False)
            await aio.sleep(0.1)
            mock_expire.assert_called_once()

    def test_cflush(self, tmp_path):
        """cflush вызывает file.flush()."""
        path = tmp_path / 'test.log'
        with init_handler(AsyncFileHandler, file_path=path) as handler:
            handler.setFormatter(MonocolorFormatter())
            record = log_record()
            handler.chandle(record)
            handler.cflush()
            content = path.read_text()
            assert 'test test_arg1' in content

    def test_chandle(self, tmp_path):
        """chandle вызывает file.write(msg)."""
        path = tmp_path / 'test.log'
        with init_handler(AsyncFileHandler, file_path=path) as handler:
            handler.setFormatter(MonocolorFormatter())
            record = log_record()
            handler.chandle(record)
            assert len(handler.file.buffer) == 1


class TestLogFile:
    def test_init_path_dir(self, tmp_path):
        """Если передан путь к директории, добавляется log.log."""
        lf = LogFile(path=tmp_path)
        assert lf._path == tmp_path / 'log.log'

    def test_init_create_parent_dir(self, tmp_path):
        """Если родительская директория не существует, создаётся."""
        path = tmp_path / 'sub' / 'test.log'
        assert not path.parent.exists()
        LogFile(path=path)
        assert path.parent.exists()

    def test_init_stream_mode(self):
        """Если передан stream, mode='stream' и exp_act=no_act."""
        stream = StringIO()
        lf = LogFile(stream=stream)
        assert lf.mode == 'stream'
        assert lf.stream is stream
        assert lf.exp_act == lf.no_act

    def test_init_on_expire_delete(self, tmp_path):
        """on_expire='delete' → exp_act=delete."""
        lf = LogFile(path=tmp_path / 'test.log', on_expire='delete')
        assert lf.exp_act == lf.delete

    def test_init_on_expire_compress(self, tmp_path):
        """on_expire='compress' → exp_act=compress."""
        lf = LogFile(path=tmp_path / 'test.log', on_expire='compress')
        assert lf.exp_act == lf.compress

    def test_init_default_compressor(self, tmp_path):
        """compressor по умолчанию — zip_compressor."""
        lf = LogFile(path=tmp_path / 'test.log')
        assert lf.compressor is zip_compressor

    def test_init_custom_compressor(self, tmp_path):
        """Переданный компрессор сохраняется."""
        def my_compressor(p, d): pass
        lf = LogFile(path=tmp_path / 'test.log', compressor=my_compressor)
        assert lf.compressor is my_compressor

    def test_init_current_log_dt(self, tmp_path):
        """Если current_log_dt не передан, берётся get_current_time()."""
        lf = LogFile(path=tmp_path / 'test.log')
        assert lf.current_log_dt is not None

    def test_path_stream_mode(self):
        """В stream-режиме path возвращает Path()."""
        lf = LogFile(stream=StringIO())
        assert lf.path == Path()

    def test_path_no_rotation(self, tmp_path):
        """Без rotation_by_dt возвращает _path."""
        lf = LogFile(path=tmp_path / 'test.log', rotation_by_dt=False)
        assert lf.path == lf._path

    def test_path_with_rotation(self, tmp_path):
        """С rotation_by_dt возвращает path_with_dt()."""
        lf = LogFile(path=tmp_path / 'test.log', rotation_by_dt=True)
        assert lf.path == lf.path_with_dt()

    def test_path_with_dt_stream(self):
        """В stream-режиме path_with_dt возвращает Path()."""
        lf = LogFile(stream=StringIO())
        assert lf.path_with_dt() == Path()

    def test_path_with_dt_format(self, tmp_path):
        """path_with_dt возвращает путь с _YYYY_MM_DD."""
        lf = LogFile(path=tmp_path / 'test.log', rotation_by_dt=True)
        dt_str = lf.current_log_dt.strftime('_%Y_%m_%d')
        expected = tmp_path / f'test{dt_str}.log'
        assert lf.path_with_dt() == expected

    def test_path_with_dt_cached(self, tmp_path):
        """path_with_dt кешируется (lru_cache)."""
        lf = LogFile(path=tmp_path / 'test.log', rotation_by_dt=True)
        first = lf.path_with_dt()
        second = lf.path_with_dt()
        assert first is second

    def test_check_expired_max_bytes(self, tmp_path):
        """Превышение max_bytes → True."""
        path = tmp_path / 'test.log'
        path.write_text('x' * 100)
        lf = LogFile(path=path, max_bytes=50)
        assert lf.check_expired() is True

    def test_check_expired_max_bytes_not_exceeded(self, tmp_path):
        """max_bytes не превышен → False."""
        path = tmp_path / 'test.log'
        path.write_text('x' * 10)
        lf = LogFile(path=path, max_bytes=50)
        assert lf.check_expired() is False

    def test_check_expired_rotation_dt(self, tmp_path):
        """Смена даты при rotation_by_dt=True → True."""
        lf = LogFile(path=tmp_path / 'test.log', rotation_by_dt=True)
        # подменяем current_log_dt на вчера
        from datetime import timedelta
        lf.current_log_dt = lf.current_log_dt - timedelta(days=1)
        assert lf.check_expired() is True

    def test_check_expired_false(self, tmp_path):
        """Ни одно условие не выполнено → False."""
        path = tmp_path / 'test.log'
        path.write_text('test')
        lf = LogFile(path=path, max_bytes=100)
        assert lf.check_expired() is False

    def test_open_stream_mode(self):
        """В stream-режиме open возвращает stream."""
        stream = StringIO()
        lf = LogFile(stream=stream)
        assert lf.open('w') is stream

    def test_open_file(self, tmp_path):
        """open создаёт/открывает файл в нужном режиме."""
        path = tmp_path / 'test.log'
        lf = LogFile(path=path)
        f = lf.open('a')
        assert not f.closed
        assert f.mode == 'a'
        f.close()

    def test_open_not_found(self, tmp_path):
        """FileNotFoundError → создаёт папку/файл, открывает."""
        path = tmp_path / 'newdir' / 'test.log'
        lf = LogFile(path=path)
        f = lf.open('a')
        assert path.exists()
        assert not f.closed
        f.close()

    def test_open_reuse(self, tmp_path):
        """Переиспользует открытый stream, если режим совпадает."""
        path = tmp_path / 'test.log'
        lf = LogFile(path=path)
        f1 = lf.open('a')
        f2 = lf.open('a')
        assert f1 is f2
        f1.close()

    def test_open_different_mode(self, tmp_path):
        """При смене режима открывает новый stream."""
        path = tmp_path / 'test.log'
        lf = LogFile(path=path)
        f1 = lf.open('a')
        f2 = lf.open('rb')
        assert f1 is not f2
        f1.close()
        f2.close()

    def test_write(self, tmp_path):
        """write добавляет строку в буфер."""
        lf = LogFile(path=tmp_path / 'test.log')
        lf.write('line1')
        assert lf.buffer == ['line1']

    def test_write_buffer_full(self, tmp_path):
        """При переполнении буфера вызывается flush."""
        lf = LogFile(path=tmp_path / 'test.log', buffer_size=2)
        lf.write('line1')
        lf.write('line2')
        # буфер должен сброситься при третьей записи
        lf.write('line3')
        # после flush буфер пуст, потом добавляется line3
        assert lf.buffer == ['line3']
        # данные должны быть в файле
        content = (tmp_path / 'test.log').read_text()
        assert 'line1' in content
        assert 'line2' in content

    def test_flush(self, tmp_path):
        """flush сбрасывает буфер в файл."""
        path = tmp_path / 'test.log'
        lf = LogFile(path=path)
        lf.write('line1')
        lf.write('line2')
        lf.flush()
        assert lf.buffer == []
        content = path.read_text()
        assert content == 'line1\nline2\n'

    def test_flush_empty_buffer(self, tmp_path):
        """flush с пустым буфером ничего не делает."""
        lf = LogFile(path=tmp_path / 'test.log')
        lf.flush()  # не должно упасть
        assert lf.buffer == []

    @pytest.mark.asyncio
    async def test_awrite(self, tmp_path):
        """awrite добавляет строку в буфер."""
        lf = LogFile(path=tmp_path / 'test.log')
        await lf.awrite('line1')
        assert lf.buffer == ['line1']
        # отменяем отложенную задачу, чтобы не мешала
        if lf.delayed_flush:
            lf.delayed_flush.cancel()

    @pytest.mark.asyncio
    async def test_awrite_buffer_full(self, tmp_path):
        """При переполнении буфера awrite вызывает aflush."""
        lf = LogFile(path=tmp_path / 'test.log', buffer_size=2)
        await lf.awrite('line1')
        await lf.awrite('line2')
        await lf.awrite('line3')
        # отменяем delayed_flush, чтобы не было гонки
        if lf.delayed_flush:
            lf.delayed_flush.cancel()
        assert lf.buffer == ['line3']

    @pytest.mark.asyncio
    async def test_aflush(self, tmp_path):
        """aflush асинхронно сбрасывает буфер в файл."""
        path = tmp_path / 'test.log'
        lf = LogFile(path=path)
        await lf.awrite('line1')
        await lf.awrite('line2')
        if lf.delayed_flush:
            lf.delayed_flush.cancel()
        await lf.aflush()
        assert lf.buffer == []
        content = path.read_text()
        assert content == 'line1\nline2\n'

    @pytest.mark.asyncio
    async def test_daflush(self, tmp_path):
        """daflush вызывает aflush после задержки."""
        path = tmp_path / 'test.log'
        lf = LogFile(path=path)
        await lf.awrite('line1')
        # daflush запущен через create_task, ждём
        await aio.sleep(0.05)
        assert lf.buffer == []
        content = path.read_text()
        assert content == 'line1\n'

    def test_delete_file(self, tmp_path):
        """delete удаляет файл."""
        path = tmp_path / 'test.log'
        path.write_text('test')
        lf = LogFile(path=path)
        lf.delete()
        assert not path.exists()

    def test_delete_not_exists(self, tmp_path):
        """delete не падает, если файла нет."""
        path = tmp_path / 'test.log'
        lf = LogFile(path=path)
        lf.delete()  # не должно упасть

    def test_delete_stream(self):
        """delete в stream-режиме закрывает stream."""
        stream = StringIO()
        lf = LogFile(stream=stream)
        lf.delete()
        assert stream.closed

    def test_compress(self, tmp_path):
        """compress вызывает компрессор, чистит кеш, удаляет файл."""
        path = tmp_path / 'test.log'
        path.write_text('log data')
        compressor = Mock()
        lf = LogFile(path=path, on_expire='compress', compressor=compressor)
        # заполняем кеш
        _ = lf.path_with_dt()
        lf.compress()
        compressor.assert_called_once()
        args = compressor.call_args[0]
        assert args[0] == path
        assert not path.exists()

    def test_compress_error(self, tmp_path):
        """Ошибка компрессора → warn, файл всё равно удаляется."""
        path = tmp_path / 'test.log'
        path.write_text('log data')
        def failing_compressor(p, d):
            raise RuntimeError('compression failed')
        lf = LogFile(path=path, on_expire='compress', compressor=failing_compressor)
        with pytest.warns(UserWarning, match='Error compressing log file'):
            lf.compress()
        assert not path.exists()

    def test_expire(self, tmp_path):
        """expire вызывает exp_act под блокировкой."""
        path = tmp_path / 'test.log'
        path.write_text('test')
        lf = LogFile(path=path, on_expire='delete')
        lf.expire()
        assert not path.exists()


class TestZipCompressor:
    """Тесты для zip_compressor."""

    def test_zip_compressor_creates_zip(self, tmp_path):
        """zip_compressor создаёт zip-архив с содержимым файла."""
        log_path = tmp_path / 'test.log'
        log_path.write_text('log content')
        data = open(log_path, 'rb')
        zip_compressor(log_path, data)
        data.close()
        # должен появиться .zip файл
        zip_files = list(tmp_path.glob('*.zip'))
        assert len(zip_files) == 1
        zip_path = zip_files[0]
        # проверяем содержимое
        with ZipFile(zip_path, 'r') as zf:
            assert 'test.log' in zf.namelist()
            assert zf.read('test.log') == b'log content'

    def test_zip_compressor_multiple(self, tmp_path):
        """При повторном вызове создаётся новый zip-файл."""
        log_path = tmp_path / 'test.log'
        log_path.write_text('log content')
        data = open(log_path, 'rb')
        zip_compressor(log_path, data)
        data.close()
        data = open(log_path, 'rb')
        zip_compressor(log_path, data)
        data.close()
        zip_files = sorted(tmp_path.glob('*.zip'))
        assert len(zip_files) == 2