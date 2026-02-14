import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# TODO: доработать парсинг вложенных классов
# from pydantic.dataclasses import dataclass # noqa к такому мой env пока не готов
from src.env import EnvironTools, EnvValidationError, environ
from src.environ import Env


class TestEnv:
    def test_creation(self):
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
            TEST_ENV_INT: int
            TEST_ENV_STR: str
            TEST_ENV_BOOL: bool
            TEST_ENV_FLOAT: float
            TEST_ENV_PATH: Path
            TEST_ENV_LIST: list[int]
            TEST_ENV_DICT: dict[str, int]
            # TEST_ENV_CLASS: InnerClass  # noqa к такому мой env пока не готов

        env = TestEnv()
        env2 = TestEnv()

        assert env is env2

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
            TEST_ENV_INT: int

        try:
            TestEnv()
        except EnvValidationError as e:
            str(e)

        with pytest.raises(EnvValidationError):
            TestEnv()

        @environ()
        class TestEnv2:
            REQ_FIELD: str

        with pytest.raises(EnvValidationError):
            TestEnv2()

        @environ()
        class TestEnv3:
            TEST_JSON: dict[str, str]
    
        with pytest.raises(EnvValidationError):
            TestEnv3()

    @patch.dict(os.environ, 
                {"TEST_ENV": "1"}
            )
    def test_refresh(self):
        @environ()
        class TestEnv(EnvironTools):
            TEST_ENV: int

        env = TestEnv()
        assert env.TEST_ENV == 1

        os.environ["TEST_ENV"] = "2"

        env.refresh()
        assert env.TEST_ENV == 2

    @patch.dict(os.environ, 
                {
                    "TEST_ENV": "1",
                    "TEST_BOOL": "true",
                    "TEST_DICT": '{"a": 1}'
                }
        )
    def test_save(self):
        text = 'TEST_ENV=1\nTEST_BOOL=true\nTEST_DICT={"a":1}'
        with tempfile.NamedTemporaryFile('w', suffix='.env') as f:
            @environ(Path(f.name))
            class TestEnv(EnvironTools):
                TEST_ENV: int
                TEST_BOOL: bool
                TEST_DICT: dict[str, int]

            p = Path(f.name)
            env = TestEnv()
            env.save(p)
            assert p.exists()
            assert p.read_text() == text

        with tempfile.NamedTemporaryFile('w', suffix='.env') as f:
            p = Path(f.name)
            env.save(p, full_env=True)
            assert p.exists()
            assert p.read_text() != text

    def test_k8s_env(self):
        pass

    def test_zero_field_as_default(self):
        @environ()
        class TestEnv(EnvironTools):
            TEST_ENV: int = 0

        env = TestEnv()
        assert env.TEST_ENV == 0