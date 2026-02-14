from src.utils.logging.formatters import MonocolorFormatter, ColoredConsoleFormatter, JsonFormatter
from colorama import Fore
import pytest
from logging import LogRecord, getLogger
from src.utils.logging.handlers import AsyncConsoleHandler, AsyncFileHandler, RawQueueHandler
import multiprocessing as mp
import weakref
from src.utils.logging import config_async_logging
import os
import asyncio
from tempfile import NamedTemporaryFile


class TestLogging:
    @pytest.mark.parametrize(
        "text, args, expected, explen",
        [
            ('test simple text %s', (1,), 'test simple text 1', 100),
        ],
    )
    def test_monocolor_format(self, text, args, expected, explen):
        fmt = MonocolorFormatter()
        record = LogRecord('test', 20, 'tests', 123, text, args, None)
        for arg in args:
            setattr(record, str(arg), arg)
        result = fmt.format(record)
        assert isinstance(result, str)
        assert expected in result
        assert Fore.RESET not in result
        assert len(result) == explen

    @pytest.mark.parametrize(
        "text, args, expected, explen",
        [
            ('test simple text %s', (1,), 'test simple text 1', 160),
        ],
    )
    def test_colored_format(self, text, args, expected, explen):
        fmt = ColoredConsoleFormatter()
        custom = ColoredConsoleFormatter(custom_colors={'levelname': Fore.YELLOW})
        record = LogRecord('test', 20, 'tests', 123, text, args, None)
        for arg in args:
            setattr(record, str(arg), arg)
        result = fmt.format(record)
        assert isinstance(result, str)
        assert expected in result
        assert Fore.RESET in result
        assert len(result) == explen

    @pytest.mark.parametrize(
        "text, args, expected, explen",
        [
            ('test simple text %s', (1,), 'test simple text 1', 161),
        ],
    )
    def test_json_format(self, text, args, expected, explen):
        fmt = JsonFormatter()
        record = LogRecord('test', 20, 'tests', 123, text, args, None)
        for arg in args:
            setattr(record, f'a{arg}', arg)
        result = fmt.format(record)
        assert isinstance(result, str)
        assert expected in result
        assert Fore.RESET not in result
        assert len(result) == explen
        assert '"extra":{"a1":1}' in result

    @pytest.mark.parametrize(
        "text, args, expected, explen",
        [
            ('test simple text %s', (1,), 'test simple text 1', 155),
        ],
    )
    def test_que_handler(self, text, args, expected, explen):
        ctx = mp.get_context('spawn')
        que = ctx.Queue()
        record = LogRecord('test', 20, 'tests', 123, text, args, None)
        hndlr = RawQueueHandler(que)
        hndlr.emit(record)
        assert que.qsize() == 1
        class SomeObj:
            pass
        a = SomeObj()
        args = list(args)
        args.append(weakref.ref(a))
        args = tuple(args)
        record2 = LogRecord('test', 20, 'tests', 123, text, args, None)
        hndlr.emit(record2)
        assert que.qsize() == 1

    @pytest.mark.asyncio
    async def test_config(self):
        config_async_logging()
        logger = getLogger()
        assert isinstance(logger.handlers[0], AsyncConsoleHandler)

        mf = MonocolorFormatter()
        config_async_logging(mf)
        assert isinstance(logger.handlers[0].formatter, MonocolorFormatter)

        os.environ['LOG_CONSOLE'] = 'true'
        os.environ['LOG_CONSOLE_COLORS'] = 'false'
        config_async_logging()
        os.environ['LOG_CONSOLE_COLORS'] = 'true'
        config_async_logging()

        ctx = mp.get_context('spawn')
        que = ctx.Queue()
        config_async_logging(mp_que=que)

        h = AsyncFileHandler('log.log')
        h.setLevel(0)
        hndlrs = [h]
        config_async_logging(handlers=hndlrs)

        os.environ['LOG_FILE_JSON'] = 'true'
        os.environ['LOG_FILE'] = 'true'
        config_async_logging()

        os.environ['LOG_FILE_JSON'] = 'false'
        config_async_logging(formatter=MonocolorFormatter())

    @pytest.mark.asyncio
    async def test_async_logging(self):
        with NamedTemporaryFile('a', encoding='utf-8', prefix='log', suffix='.log') as f:
            ch = AsyncConsoleHandler()
            ch.setFormatter(ColoredConsoleFormatter())
            fh = AsyncFileHandler(f.name)
            fh.setFormatter(MonocolorFormatter())
            config_async_logging(handlers=[ch, fh])
            logger = getLogger()

            for i in range(10):
                logger.info(i)

            await asyncio.sleep(0.1)

            with open(f.name, 'r', encoding='utf-8') as rf:
                assert len(rf.readlines()) == 10

            for i in range(500):
                logger.info(i)

            await asyncio.sleep(0.1)

            with open(f.name, 'r', encoding='utf-8') as rf:
                assert len(rf.readlines()) == 510