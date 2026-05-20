import os
from pathlib import Path
from unittest.mock import patch
import tempfile
import pytest

# TODO: доработать парсинг вложенных классов
# from pydantic.dataclasses import dataclass # noqa к такому мой env пока не готов
from src.magutils.env_utils import EnvValidationError, environ, field
from src.magutils.env_utils.mixins import RedisMixin, LoggingMixin, DBMixin, CORSMixin


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

    def test_yaml_basic_functionality(self):
        """Тест чтения простого значения из YAML файла."""
        pytest.importorskip('yaml')
        import yaml
        import tempfile
        
        with tempfile.NamedTemporaryFile('+w', suffix='.yaml', encoding='utf-8') as f:
            yaml_data = {'simple_key': 'simple_value', 'number': 42}
            yaml.dump(yaml_data, f)
            f.flush()
            
            from src.magutils.env_utils.ext import yaml as yaml_factory
            
            # Создаем фабрику
            factory = yaml_factory(f.name, 'simple_key')
            
            # Вызываем фабрику с контекстом
            ctx = {}
            result = factory(ctx)
            assert result == 'simple_value'
            
            # Проверяем кэширование
            assert str(f.name) in ctx
            assert ctx[str(f.name)] == yaml_data

    def test_yaml_nested_path(self):
        """Тест чтения вложенного значения через точечную нотацию."""
        pytest.importorskip('yaml')
        import yaml
        import tempfile
        
        with tempfile.NamedTemporaryFile('+w', suffix='.yaml', encoding='utf-8') as f:
            yaml_data = {
                'services': {
                    'notification': {
                        'ports': [8080, 8081],
                        'enabled': True
                    }
                }
            }
            yaml.dump(yaml_data, f)
            f.flush()
            
            from src.magutils.env_utils.ext import yaml as yaml_factory
            
            factory = yaml_factory(f.name, 'services.notification.ports')
            ctx = {}
            result = factory(ctx)
            assert result == [8080, 8081]

    def test_yaml_caching(self):
        """Тест кэширования YAML файла в контексте."""
        pytest.importorskip('yaml')
        import yaml
        import tempfile
        
        with tempfile.NamedTemporaryFile('+w', suffix='.yaml', encoding='utf-8') as f:
            yaml_data = {'key1': 'value1', 'key2': 'value2'}
            yaml.dump(yaml_data, f)
            f.flush()
            
            from src.magutils.env_utils.ext import yaml as yaml_factory
            
            factory1 = yaml_factory(f.name, 'key1')
            factory2 = yaml_factory(f.name, 'key2')
            
            ctx = {}
            result1 = factory1(ctx)
            result2 = factory2(ctx)
            
            # Файл должен быть прочитан только один раз
            assert result1 == 'value1'
            assert result2 == 'value2'
            # В контексте должен быть только один ключ с содержимым файла
            assert len(ctx) == 1
            assert str(f.name) in ctx

    def test_yaml_missing_key_error(self):
        """Тест ошибки при отсутствии ключа в YAML файле."""
        pytest.importorskip('yaml')
        import yaml
        import tempfile
        
        with tempfile.NamedTemporaryFile('+w', suffix='.yaml', encoding='utf-8') as f:
            yaml_data = {'existing_key': 'value'}
            yaml.dump(yaml_data, f)
            f.flush()
            
            from src.magutils.env_utils.ext import yaml as yaml_factory
            
            factory = yaml_factory(f.name, 'non.existing.key')
            ctx = {}
            
            with pytest.raises(KeyError, match='Key.*not found'):
                factory(ctx)

    def test_yaml_missing_file_error(self):
        """Тест ошибки при отсутствии YAML файла."""
        pytest.importorskip('yaml')
        import tempfile
        import os
        
        from src.magutils.env_utils.ext import yaml as yaml_factory
        
        # Создаем временный файл и сразу удаляем его
        with tempfile.NamedTemporaryFile('+w', suffix='.yaml', encoding='utf-8', delete=False) as f:
            f.write('key: value')
            temp_path = f.name
        
        os.unlink(temp_path)  # Удаляем файл
        
        factory = yaml_factory(temp_path, 'key')
        ctx = {}
        
        with pytest.raises(FileNotFoundError):
            factory(ctx)

    @patch.dict(os.environ, {'DB_HOST': 'postgresql'})
    def test_yaml_integration_with_environ(self):
        """Тест интеграции YAML фабрики с environ()."""
        pytest.importorskip('yaml')
        import yaml
        import tempfile
        
        with tempfile.NamedTemporaryFile('+w', suffix='.yaml', encoding='utf-8') as f:
            yaml_data = {
                'services': {
                    'app': {
                        'ports': [3000, 3001],
                        'debug': True
                    }
                }
            }
            yaml.dump(yaml_data, f)
            f.flush()
            
            from src.magutils.env_utils.ext import yaml as yaml_factory
            from src.magutils.env_utils import environ, field
            
            @environ()
            class EnvWithYaml:
                # Значение из .env файла (переменная окружения)
                DB_HOST: str = field()
                # Значение из YAML файла
                APP_PORTS: list = field(default_factory=yaml_factory(f.name, 'services.app.ports'))
                APP_DEBUG: bool = field(default_factory=yaml_factory(f.name, 'services.app.debug'))
                # Значение по умолчанию, если не найдено ни в .env, ни в YAML
                DEFAULT_VALUE: int = field(999)
            
            env = EnvWithYaml()
            
            assert env.DB_HOST == 'postgresql'  # Из переменных окружения
            assert env.APP_PORTS == [3000, 3001]  # Из YAML файла
            assert env.APP_DEBUG is True  # Из YAML файла
            assert env.DEFAULT_VALUE == 999  # Значение по умолчанию

    def test_yaml_priority_over_default(self):
        """Тест приоритета YAML значения над значением по умолчанию."""
        pytest.importorskip('yaml')
        import yaml
        import tempfile
        
        with tempfile.NamedTemporaryFile('+w', suffix='.yaml', encoding='utf-8') as f:
            yaml_data = {'config_value': 'from_yaml'}
            yaml.dump(yaml_data, f)
            f.flush()
            
            from src.magutils.env_utils.ext import yaml as yaml_factory
            from src.magutils.env_utils import environ, field
            
            @environ()
            class EnvYamlPriority:
                # YAML значение должно использоваться вместо значения по умолчанию
                CONFIG_VALUE: str = field(
                    'default_value',
                    default_factory=yaml_factory(f.name, 'config_value')
                )
            
            env = EnvYamlPriority()
            assert env.CONFIG_VALUE == 'from_yaml'