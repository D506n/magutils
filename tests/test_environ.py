import os
from pathlib import Path
from unittest.mock import patch
import tempfile
import pytest

# TODO: доработать парсинг вложенных классов
# from pydantic.dataclasses import dataclass # noqa к такому мой env пока не готов
from src.utils.env import EnvValidationError, environ, field
from src.utils.env.mixins import RedisMixin, LoggingMixin, DBMixin, CORSMixin


class TestEnv:
    def test_creation(self):
        @environ()
        class Env():
            A = field(1)
        e1 = Env()
        e2 = Env()
        assert e1 is e2

    @patch.dict(os.environ, 
                {
                    'TEST_ENV_INT': "1", 
                    "TEST_ENV_STR": "some_string",
                    "TEST_ENV_BOOL": "True",
                    "TEST_ENV_FLOAT": "3.14",
                    "TEST_ENV_PATH": './tests/test_environ.py',
                    "TEST_ENV_LIST": '[1, 2, 3]',
                    "TEST_ENV_DICT": '{"a": 1}',
                    # "TEST_ENV_CLASS": '{"field": 1}' # noqa к такому мой env пока не готов
                }
            )
    def test_environ_decorator(self):
        # @dataclass
        # class InnerClass:
        #     field: int
        # noqa к такому мой env пока не готов

        @environ()
        class TestEnv:
            TEST_ENV_INT: int = field()
            TEST_ENV_STR: str = field()
            TEST_ENV_BOOL: bool = field()
            TEST_ENV_FLOAT: float = field()
            TEST_ENV_PATH: Path = field()
            TEST_ENV_LIST: list[int] = field()
            TEST_ENV_DICT: dict[str, int] = field()
            # TEST_ENV_CLASS: InnerClass  # noqa к такому мой env пока не готов

        env = TestEnv()
        env2 = TestEnv()
        first_str = str(env)
        env.SOME_UNEXCPECTED_FIELD = 1
        second_str = str(env)
        assert env is env2
        assert first_str == second_str

        assert isinstance(env.TEST_ENV_INT, int) and env.TEST_ENV_INT == 1
        assert isinstance(env.TEST_ENV_STR, str) and env.TEST_ENV_STR == 'some_string' # noqa
        assert isinstance(env.TEST_ENV_BOOL, bool) and env.TEST_ENV_BOOL
        assert isinstance(env.TEST_ENV_FLOAT, float) and env.TEST_ENV_FLOAT == 3.14 # noqa
        assert isinstance(env.TEST_ENV_PATH, Path) and env.TEST_ENV_PATH.exists() # noqa
        assert isinstance(env.TEST_ENV_LIST, list) and env.TEST_ENV_LIST[0] == 1
        assert isinstance(env.TEST_ENV_DICT, dict) and env.TEST_ENV_DICT['a'] == 1 # noqa
        # assert isinstance(env.TEST_ENV_CLASS, InnerClass) and env.TEST_ENV_CLASS.field1 == 1 # noqa  # noqa к такому мой env пока не готов

    @patch.dict(os.environ, 
                {
                    'TEST_ENV_INT': "error",
                    'TEST_JSON': '{"a": 1}'
                }
            )
    def test_env_parsing_error(self):
        @environ()
        class TestEnv:
            TEST_ENV_INT: int = field()

        try:
            TestEnv()
        except EnvValidationError as e:
            str(e)

        with pytest.raises(EnvValidationError):
            TestEnv()

        @environ()
        class TestEnv2:
            REQ_FIELD: str = field()

        with pytest.raises(EnvValidationError):
            TestEnv2()

        @environ()
        class TestEnv3:
            TEST_JSON: dict[str, str] = field()

        with pytest.raises(EnvValidationError):
            TestEnv3()

    def test_k8s_env(self):
        pass

    def test_zero_field_as_default(self):
        @environ()
        class TestEnv():
            TEST_ENV: int = field(0)

        env = TestEnv()
        assert env.TEST_ENV == 0

    def test_custom_env_file(self):
        with tempfile.NamedTemporaryFile('+r', encoding='utf-8') as f:
            f.write('A=1')
            f.flush()

            @environ(Path(f.name))
            class TestEnv:
                A: int = field()

            env = TestEnv()
            assert env.A == 1

    def test_field_required_error(self):
        @environ()
        class TestEnv:
            UNIQUE_FIELD_100_PERCENT: int = field()

        with pytest.raises(EnvValidationError):
            TestEnv()

    def test_field_factory(self):
        @environ()
        class TestEnv:
            TEST_FACTORY: int = field(default_factory=lambda: 2+2)
            TEST_FACTORY2: int = field(default_factory=lambda x: x['TEST_FACTORY']*2)

        env = TestEnv()
        assert env.TEST_FACTORY == 4
        assert env.TEST_FACTORY2 == 8

    @patch.dict(os.environ, 
                {
                    'FIELDA': "123"
                }
            )
    def test_alias_field(self):
        @environ()
        class TestEnv():
            FIELDB: int = field(aliases=['FIELDA'])

        env = TestEnv()

        assert env.FIELDB == 123


    @patch.dict(os.environ, 
                {
                    'PREFIX_FIELDC': "123"
                }
            )
    def test_prefix(self):
        @environ(prefix='PREFIX_')
        class TestEnv():
            FIELDC: int = field()

        env = TestEnv()

        assert env.FIELDC == 123
    def test_mixins(self):
        """Тестирование добавления миксинов в окружение."""
        # Тест LoggingMixin
        @environ()
        class EnvWithLogging(LoggingMixin):
            pass

        env = EnvWithLogging()
        assert env.LOG_LEVEL == 'INFO'
        assert env.CONSOLE_LOG_JSON is False
        assert env.CONSOLE_LOG_LEVEL == 'INFO'
        assert env.CONSOLE_LOG_COLOR is True
        assert env.CONSOLE_LOG_NOCUT is False
        assert env.FILE_LOG_LEVEL == 'INFO'
        assert env.FILE_LOG_PATH == Path('./data/logs/log.log')
        assert env.FILE_LOG_NOCUT is True
        assert env.FILE_LOG_ON_EXPIRE == 'compress'
        assert env.FILE_LOG_MAXBYTES is None
        assert env.FILE_LOG_ROTATION_BY_DT is True

        # Тест DBMixin
        @environ()
        class EnvWithDB(DBMixin):
            pass

        env = EnvWithDB()
        assert env.DB_TYPE == 'sqlite'
        assert env.DB_USERNAME is None
        assert env.DB_PASSWORD is None
        assert env.DB_HOST is None
        assert env.DB_PORT is None
        assert env.DB_NAME is None
        assert env.DB_PATH is None

        # Тест RedisMixin
        @environ()
        class EnvWithRedis(RedisMixin):
            pass

        env = EnvWithRedis()
        assert env.REDIS_HOST == 'localhost'
        assert env.REDIS_PORT == 6379
        assert env.REDIS_DB == 0
        assert env.REDIS_PASSWORD is None

        # Тест CORSMixin
        @environ()
        class EnvWithCORS(CORSMixin):
            pass

        env = EnvWithCORS()
        # default_factory возвращает строку JSON, которая должна быть распарсена в список
        assert env.CORS_ALLOW_ORIGINS == ["http://localhost:5173"]
        assert env.CORS_ALLOW_CREDENTIALS is True
        assert env.CORS_ALLOW_METHODS == ["*"]
        assert env.CORS_ALLOW_HEADERS == ["*"]

        # Комбинированный тест: все миксины вместе
        @environ()
        class EnvAll(LoggingMixin, DBMixin, RedisMixin, CORSMixin):
            pass

        env_all = EnvAll()
        # Проверяем несколько полей из каждого миксина
        assert env_all.LOG_LEVEL == 'INFO'
        assert env_all.DB_TYPE == 'sqlite'
        assert env_all.REDIS_HOST == 'localhost'
        assert env_all.CORS_ALLOW_ORIGINS == ["http://localhost:5173"]