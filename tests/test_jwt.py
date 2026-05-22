import base64
import hashlib
import hmac
import os
import time
from unittest.mock import patch, MagicMock
import pytest
import orjson
from magutils.jwt import (
    jwt_encode,
    jwt_decode,
    Config,
    DecodeResult,
)


class TestJWT:
    """Тесты для функций JWT encode/decode."""

    def setup_method(self):
        """Сброс состояния Config перед каждым тестом."""
        Config._secret = None
        Config._hmac = None
        Config._precomp_header = None
        Config._default_header = {"alg": "HS256", "typ": "JWT"}

    def test_encode_basic(self):
        """Тест кодирования JWT с секретом."""
        payload = {"sub": "123", "name": "John"}
        secret = "mysecret"
        token = jwt_encode(payload, secret)
        assert isinstance(token, str)
        parts = token.split('.')
        assert len(parts) == 3
        header_b64, payload_b64, signature_b64 = parts
        # Проверяем, что header соответствует ожидаемому
        header = orjson.loads(base64.urlsafe_b64decode(header_b64 + '=='))
        assert header == {"alg": "HS256", "typ": "JWT"}
        # Проверяем payload
        decoded_payload = orjson.loads(base64.urlsafe_b64decode(payload_b64 + '=='))
        assert decoded_payload == payload
        # Проверяем подпись
        msg = f"{header_b64}.{payload_b64}".encode()
        expected_hmac = hmac.new(secret.encode(), msg, hashlib.sha256)
        expected_sig = base64.urlsafe_b64encode(expected_hmac.digest()).rstrip(b'=').decode()
        assert signature_b64 == expected_sig

    def test_encode_with_custom_headers(self):
        """Тест кодирования с кастомными заголовками."""
        payload = {"foo": "bar"}
        secret = "secret"
        headers = {"alg": "HS256", "typ": "JWT", "kid": "123"}
        token = jwt_encode(payload, secret, headers)
        parts = token.split('.')
        header = orjson.loads(base64.urlsafe_b64decode(parts[0] + '=='))
        assert header == headers

    def test_encode_uses_config_secret_if_none(self):
        """Тест, что encode использует секрет из Config, если не передан."""
        with patch.dict(os.environ, {'JWT_SECRET': 'envsecret'}):
            Config._secret = None
            payload = {"test": 1}
            token = jwt_encode(payload)
            # Проверим, что подпись верна с envsecret
            parts = token.split('.')
            msg = f"{parts[0]}.{parts[1]}".encode()
            expected_hmac = hmac.new(b'envsecret', msg, hashlib.sha256)
            expected_sig = base64.urlsafe_b64encode(expected_hmac.digest()).rstrip(b'=').decode()
            assert parts[2] == expected_sig

    def test_encode_raises_if_no_secret(self):
        """Тест, что encode вызывает KeyError, если секрет не установлен."""
        with patch.dict(os.environ, {}, clear=True):
            Config._secret = None
            with pytest.raises(KeyError, match='JWT secret not set!'):
                jwt_encode({"test": 1})

    def test_decode_valid_token(self):
        """Тест декодирования валидного токена."""
        payload = {"sub": "user", "exp": time.time() + 3600}
        secret = "secret"
        token = jwt_encode(payload, secret)
        result = jwt_decode(token, secret)
        assert isinstance(result, dict)
        assert 'headers' in result
        assert 'payload' in result
        assert 'signature' in result
        assert result['payload'] == payload
        assert result['headers'] == {"alg": "HS256", "typ": "JWT"}
        assert isinstance(result['signature'], bytes)

    def test_decode_invalid_signature(self):
        """Тест декодирования с неверной подписью."""
        payload = {"sub": "user"}
        secret = "secret"
        token = jwt_encode(payload, secret)
        print(token)
        # Изменяем один символ в подписи
        parts = token.split('.')
        corrupted = parts[2][0:] + ('a' if parts[2][-1] != 'a' else 'b')
        corrupted_token = f"{parts[0]}.{parts[1]}.{corrupted}"
        with pytest.raises(ValueError, match='Invalid token'):
            jwt_decode(corrupted_token, secret)

    def test_decode_expired_token(self):
        """Тест декодирования истёкшего токена."""
        payload = {"sub": "user", "exp": time.time() - 1}
        secret = "secret"
        token = jwt_encode(payload, secret)
        with pytest.raises(ValueError, match='Invalid token'):
            jwt_decode(token, secret)

    def test_decode_malformed_token(self):
        """Тест декодирования некорректного токена (не три части)."""
        with pytest.raises(ValueError, match='Invalid token'):
            jwt_decode("invalid.token", "secret")

    def test_decode_invalid_base64(self):
        """Тест декодирования с некорректным base64."""
        with pytest.raises(ValueError, match='Invalid token'):
            jwt_decode("a.b.c", "secret")

    def test_decode_uses_config_secret_if_none(self):
        """Тест, что decode использует секрет из Config, если не передан."""
        with patch.dict(os.environ, {'JWT_SECRET': 'envsecret'}):
            Config._secret = None
            payload = {"test": 1}
            token = jwt_encode(payload, 'envsecret')
            result = jwt_decode(token)
            assert result['payload'] == payload

    def test_decode_result_typeddict(self):
        """Проверка, что DecodeResult соответствует ожидаемой структуре."""
        result = DecodeResult(headers={}, payload={}, signature=b'')
        assert isinstance(result, dict)
        assert 'headers' in result
        assert 'payload' in result
        assert 'signature' in result


class TestConfig:
    """Тесты для класса Config (метакласса)."""

    def setup_method(self):
        """Сброс состояния Config перед каждым тестом."""
        Config._secret = None
        Config._hmac = None
        Config._precomp_header = None
        Config._default_header = {"alg": "HS256", "typ": "JWT"}

    def test_secret_property_env(self):
        """Тест свойства secret, загружающего из окружения."""
        with patch.dict(os.environ, {'JWT_SECRET': 'testsecret'}):
            Config._secret = None
            assert Config.secret == 'testsecret'
            # Проверяем кэширование
            assert Config._secret == 'testsecret'

    def test_secret_property_raises_if_missing(self):
        """Тест, что secret вызывает KeyError, если переменная окружения отсутствует."""
        with patch.dict(os.environ, {}, clear=True):
            Config._secret = None
            with pytest.raises(KeyError, match='JWT secret not set!'):
                _ = Config.secret

    def test_secret_setter(self):
        """Тест сеттера secret."""
        # Устанавливаем секрет
        Config.secret = "customsecret"
        assert Config._secret == "customsecret"
        # Проверяем, что свойство возвращает установленное значение
        assert Config.secret == "customsecret"
        # Проверяем, что окружение игнорируется
        with patch.dict(os.environ, {'JWT_SECRET': 'envsecret'}):
            # _secret уже установлен, поэтому не будет загружен из окружения
            assert Config.secret == "customsecret"
        # Проверяем тип
        with pytest.raises(TypeError, match='secret must be a string'):
            Config.secret = 123
        # Проверяем, что установка секрета сбрасывает HMAC кэш?
        # Сначала создадим HMAC с предыдущим секретом
        Config._hmac = None
        hm1 = Config.hmac("customsecret")
        assert Config._hmac is not None
        # Изменяем секрет через сеттер
        Config.secret = "newsecret"
        # HMAC должен быть сброшен, потому что secret изменился
        # При следующем вызове hmac с новым секретом должен создать новый HMAC
        hm2 = Config.hmac("newsecret")
        # Убедимся, что это другой HMAC (хотя copy возвращает новый объект, но внутренний _hmac должен быть пересоздан)
        # Проверим, что _secret обновился
        assert Config._secret == "newsecret"

    def test_default_header_property(self):
        """Тест свойства default_header."""
        assert Config.default_header == {"alg": "HS256", "typ": "JWT"}
        Config.default_header = {"alg": "HS512", "typ": "JWT"}
        assert Config.default_header == {"alg": "HS512", "typ": "JWT"}
        # Проверяем, что precomp_header сбросился
        assert Config._precomp_header is None

    def test_default_header_setter_type_check(self):
        """Тест setter default_header проверяет тип."""
        with pytest.raises(TypeError, match='default_header must be a dict'):
            Config.default_header = "not a dict"

    def test_precomp_header_property(self):
        """Тест свойства precomp_header (кэширование)."""
        # Первый вызов вычисляет
        h1 = Config.precomp_header
        assert isinstance(h1, str)
        # Второй вызов использует кэш
        h2 = Config.precomp_header
        assert h1 == h2
        # Изменение default_header сбрасывает кэш
        Config.default_header = {"alg": "HS512", "typ": "JWT"}
        assert Config._precomp_header is None
        h3 = Config.precomp_header
        assert h3 != h1

    def test_hmac_method(self):
        """Тест метода hmac, создающего HMAC объект."""
        secret = "mysecret"
        hm1 = Config.hmac(secret)
        assert isinstance(hm1, hmac.HMAC)
        # Проверяем, что digest size соответствует SHA256 (32 байта)
        assert hm1.digest_size == 32
        # Проверяем кэширование при том же секрете
        hm2 = Config.hmac(secret)
        assert hm1 != hm2  # copy возвращает новый объект
        # При новом секрете создаётся новый HMAC
        hm3 = Config.hmac("othersecret")
        assert Config._secret == "othersecret"
        # Проверяем, что HMAC обновился
        assert Config._hmac is not None