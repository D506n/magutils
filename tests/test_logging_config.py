from logging.handlers import QueueListener
from queue import Queue
from unittest.mock import Mock, patch

import pytest

from src.magutils.logging.config import config_async_logging
from src.magutils.logging import config
from src.magutils.logging.formatters import (
    ColoredConsoleFormatter,
    JsonFormatter,
    MonocolorFormatter,
)
from src.magutils.logging.handlers import AsyncConsoleHandler, AsyncFileHandler
from tests.test_logging import init_handler


class TestConfigAsyncLogging:
    """Тесты для config_async_logging — публичного API конфигурации."""

    def test_invalid_formatter(self):
        """Невалидный formatter → TypeError."""
        with pytest.raises(TypeError, match='formatter must be a Formatter'):
            config_async_logging(formatter='not_a_formatter')

    def test_with_handlers(self):
        """С переданными хендлерами — basicConfig вызывается с ними."""
        with init_handler(AsyncConsoleHandler) as handler:
            handler.setLevel('DEBUG')
            with patch('src.magutils.logging.config.basicConfig') as mock_basic:
                config_async_logging(handlers=[handler], level='DEBUG')
            mock_basic.assert_called_once()
            _, kwargs = mock_basic.call_args
            assert handler in kwargs['handlers']
            assert kwargs['level'] == 10

    def test_without_handlers_from_env(self, monkeypatch):
        """Без хендлеров — создаются из переменных окружения."""
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        mock_basic.assert_called_once()
        _, kwargs = mock_basic.call_args
        handlers = kwargs['handlers']
        assert len(handlers) == 1
        assert isinstance(handlers[0], AsyncConsoleHandler)

    def test_formatter_set_on_console_handler(self):
        """Formatter устанавливается на AsyncConsoleHandler."""
        with init_handler(AsyncConsoleHandler) as handler:
            handler.setLevel('DEBUG')
            fmt = MonocolorFormatter()
            config_async_logging(formatter=fmt, handlers=[handler], level='DEBUG')
            assert handler.formatter is fmt

    def test_colored_formatter_not_set_on_file(self, tmp_path):
        """ColoredConsoleFormatter НЕ устанавливается на AsyncFileHandler."""
        with init_handler(AsyncFileHandler, file_path=str(tmp_path / 'test.log')) as fh:
            fh.setLevel('DEBUG')
            fmt = ColoredConsoleFormatter()
            config_async_logging(formatter=fmt, handlers=[fh], level='DEBUG')
            assert fh.formatter is not fmt

    def test_mono_formatter_set_on_file(self, tmp_path):
        """MonocolorFormatter устанавливается на AsyncFileHandler."""
        with init_handler(AsyncFileHandler, file_path=str(tmp_path / 'test.log')) as fh:
            fh.setLevel('DEBUG')
            fmt = MonocolorFormatter()
            config_async_logging(formatter=fmt, handlers=[fh], level='DEBUG')
            assert fh.formatter is fmt

    def test_force_propagates_handlers(self):
        """force=True — все логгеры получают те же хендлеры."""
        with init_handler(AsyncConsoleHandler) as handler:
            handler.setLevel('DEBUG')
            with patch('src.magutils.logging.config.basicConfig'):
                with patch('src.magutils.logging.config.getLogger') as mock_get:
                    root = Mock()
                    root.handlers = [handler]
                    mock_logger = Mock(spec=['handlers', 'propagate'])
                    root.manager.loggerDict = {'test_logger': mock_logger}
                    mock_get.return_value = root
                    config_async_logging(handlers=[handler], level='DEBUG', force=True)
            assert mock_logger.handlers == root.handlers
            assert mock_logger.propagate is False

    def test_with_mp_queue(self):
        """С mp_que — создаётся QueueListener."""
        mp_que = Queue()
        with init_handler(AsyncConsoleHandler) as handler:
            handler.setLevel('DEBUG')
            config_async_logging(handlers=[handler], level='DEBUG', mp_que=mp_que)
        assert config.MP_LISTENER is not None
        assert isinstance(config.MP_LISTENER, QueueListener)
        assert config.MP_QUEUE is mp_que

    def test_handler_level_zero(self):
        """Если уровень хендлера = 0, устанавливается из level."""
        with init_handler(AsyncConsoleHandler) as handler:
            assert handler.level == 0
            with patch('src.magutils.logging.config.basicConfig'):
                config_async_logging(handlers=[handler], level='WARNING')
            assert handler.level == 30

    # ── Сценарии через переменные окружения ─────────────────────

    def test_env_console_json(self, monkeypatch):
        """CONSOLE_LOG_JSON=true → JsonFormatter."""
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        monkeypatch.setenv('TEST_CONSOLE_LOG_JSON', 'true')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        handler = kwargs['handlers'][0]
        assert isinstance(handler.formatter, JsonFormatter)

    def test_env_console_colors(self, monkeypatch):
        """CONSOLE_COLORS=true → ColoredConsoleFormatter."""
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        monkeypatch.setenv('TEST_LOG_CONSOLE_COLORS', 'true')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        handler = kwargs['handlers'][0]
        assert isinstance(handler.formatter, ColoredConsoleFormatter)

    def test_env_console_no_colors(self, monkeypatch):
        """CONSOLE_COLORS=false → MonocolorFormatter."""
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        monkeypatch.setenv('TEST_LOG_CONSOLE_COLORS', 'false')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        handler = kwargs['handlers'][0]
        assert isinstance(handler.formatter, MonocolorFormatter)

    def test_env_file_enabled(self, monkeypatch, tmp_path):
        """LOG_FILE=true → создаётся AsyncFileHandler."""
        log_path = tmp_path / 'test.log'
        monkeypatch.setenv('TEST_LOG_FILE', 'true')
        monkeypatch.setenv('TEST_LOG_FILE_PATH', str(log_path))
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        handlers = kwargs['handlers']
        assert len(handlers) == 2
        assert isinstance(handlers[0], AsyncConsoleHandler)
        assert isinstance(handlers[1], AsyncFileHandler)

    def test_env_file_json(self, monkeypatch, tmp_path):
        """LOG_FILE_JSON=true → JsonFormatter на файловом хендлере."""
        log_path = tmp_path / 'test.log'
        monkeypatch.setenv('TEST_LOG_FILE', 'true')
        monkeypatch.setenv('TEST_LOG_FILE_PATH', str(log_path))
        monkeypatch.setenv('TEST_LOG_FILE_JSON', 'true')
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        file_handler = kwargs['handlers'][1]
        assert isinstance(file_handler.formatter, JsonFormatter)

    def test_env_file_rotation(self, monkeypatch, tmp_path):
        """LOG_FILE_ROTATION_BY_DT=true."""
        log_path = tmp_path / 'test.log'
        monkeypatch.setenv('TEST_LOG_FILE', 'true')
        monkeypatch.setenv('TEST_LOG_FILE_PATH', str(log_path))
        monkeypatch.setenv('TEST_LOG_FILE_ROTATION_BY_DT', 'true')
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        file_handler = kwargs['handlers'][1]
        assert file_handler.file.rotation_by_dt is True

    def test_env_file_on_expire_compress(self, monkeypatch, tmp_path):
        """LOG_FILE_ON_EXPIRE=compress."""
        log_path = tmp_path / 'test.log'
        monkeypatch.setenv('TEST_LOG_FILE', 'true')
        monkeypatch.setenv('TEST_LOG_FILE_PATH', str(log_path))
        monkeypatch.setenv('TEST_LOG_FILE_ON_EXPIRE', 'compress')
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        file_handler = kwargs['handlers'][1]
        assert file_handler.file.on_expire == 'compress'

    def test_env_file_max_bytes(self, monkeypatch, tmp_path):
        """LOG_FILE_MAXBYTES=1024."""
        log_path = tmp_path / 'test.log'
        monkeypatch.setenv('TEST_LOG_FILE', 'true')
        monkeypatch.setenv('TEST_LOG_FILE_PATH', str(log_path))
        monkeypatch.setenv('TEST_LOG_FILE_MAXBYTES', '1024')
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='DEBUG')
        _, kwargs = mock_basic.call_args
        file_handler = kwargs['handlers'][1]
        assert file_handler.file.max_bytes == '1024'

    def test_env_no_handlers_default_console(self, monkeypatch):
        """Ничего не включено → AsyncConsoleHandler по умолчанию."""
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'false')
        monkeypatch.setenv('TEST_LOG_FILE', 'false')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='INFO')
        _, kwargs = mock_basic.call_args
        handlers = kwargs['handlers']
        assert len(handlers) == 1
        assert isinstance(handlers[0], AsyncConsoleHandler)

    def test_env_file_log_level(self, monkeypatch, tmp_path):
        """LOG_FILE_LEVEL=WARNING."""
        log_path = tmp_path / 'test.log'
        monkeypatch.setenv('TEST_LOG_FILE', 'true')
        monkeypatch.setenv('TEST_LOG_FILE_PATH', str(log_path))
        monkeypatch.setenv('TEST_LOG_FILE_LEVEL', 'WARNING')
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='INFO')
        _, kwargs = mock_basic.call_args
        file_handler = kwargs['handlers'][1]
        assert file_handler.level == 30

    def test_env_console_log_level(self, monkeypatch):
        """LOG_CONSOLE_LEVEL=ERROR."""
        monkeypatch.setenv('TEST_CONSOLE_LOG_LEVEL', 'DEBUG')
        monkeypatch.setenv('TEST_LOG_CONSOLE_LEVEL', 'ERROR')
        with patch('src.magutils.logging.config.basicConfig') as mock_basic:
            config_async_logging(env_prefix='TEST_', level='INFO')
        _, kwargs = mock_basic.call_args
        console_handler = kwargs['handlers'][0]
        assert console_handler.level == 40
