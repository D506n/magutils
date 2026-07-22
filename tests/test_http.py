from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import orjson
import pytest
from aiolimiter import AsyncLimiter

from src.magutils.http.client import LimitAwareClient
from src.magutils.http.helpers import HookCtx, QHookRunner, Storage
from src.magutils.http.request import FluentReq
from src.magutils.req_limit import Limiter


# ═══════════════════════════════════════════════════════════════════════════════
# LimitAwareClient
# ═══════════════════════════════════════════════════════════════════════════════

class TestLimitAwareClient:
    """Тесты для LimitAwareClient — HTTPX-клиент с rate limiter."""

    def test_init_without_limiter(self):
        """Инициализация без лимитера — base_url сохраняется, aiolimiter=None."""
        client = LimitAwareClient(base_url="https://example.com")
        assert client.base_url == "https://example.com"
        assert client.aiolimiter is None

    def test_init_with_limiter(self):
        """Инициализация с переданным AsyncLimiter."""
        limiter = AsyncLimiter(10, 1)
        client = LimitAwareClient(base_url="https://example.com", limiter=limiter)
        assert client.aiolimiter is limiter

    @pytest.mark.asyncio
    async def test_send_uses_custom_limiter(self):
        """send() использует переданный aiolimiter, если он задан."""
        limiter = AsyncLimiter(100, 1)
        client = LimitAwareClient(base_url="https://example.com", limiter=limiter)
        request = httpx.Request("GET", "https://example.com/test")

        with patch.object(client, "_LimitAwareClient__get_limiter", wraps=client._LimitAwareClient__get_limiter) as mock_get_limiter:
            with patch.object(httpx.AsyncClient, "send", new_callable=AsyncMock) as mock_super_send:
                mock_super_send.return_value = httpx.Response(200, request=request)
                resp = await client.send(request)

        assert resp.status_code == 200
        mock_get_limiter.assert_called_once()
        mock_super_send.assert_called_once_with(
            request, stream=False, auth=..., follow_redirects=...
        )

    @pytest.mark.asyncio
    async def test_send_uses_global_limiter_when_no_custom(self):
        """send() использует глобальный Limiter.get(), если aiolimiter не задан."""
        Limiter._Limiter__inst = None
        Limiter.set("https://anyservice.com", limit=50, per=1)

        client = LimitAwareClient(base_url="https://anyservice.com")
        request = httpx.Request("GET", "https://anyservice.com/data")

        with patch.object(httpx.AsyncClient, "send", new_callable=AsyncMock) as mock_super_send:
            mock_super_send.return_value = httpx.Response(200, request=request)
            resp = await client.send(request)

        assert resp.status_code == 200
        Limiter._Limiter__inst = None

    @pytest.mark.asyncio
    async def test_send_passes_stream_and_auth(self):
        """send() пробрасывает stream, auth и follow_redirects в super().send()."""
        client = LimitAwareClient(base_url="https://example.com", limiter=AsyncLimiter(100, 1))
        request = httpx.Request("GET", "https://example.com/stream")

        with patch.object(httpx.AsyncClient, "send", new_callable=AsyncMock) as mock_super_send:
            mock_super_send.return_value = httpx.Response(200, request=request)
            resp = await client.send(request, stream=True, auth=("user", "pass"), follow_redirects=True)

        assert resp.status_code == 200
        mock_super_send.assert_called_once_with(
            request, stream=True, auth=("user", "pass"), follow_redirects=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ROProxy
# ═══════════════════════════════════════════════════════════════════════════════

class TestROProxy:
    """Тесты для ROProxy — read-only прокси для FluentRequest."""

    def test_proxy_attributes(self):
        """ROProxy пробрасывает атрибуты из FluentRequest через геттер .get."""
        req = FluentReq("https://base.com")
        req.method("POST").url("/path").params({"q": "1"}).headers({"X-Custom": "val"})
        proxy = req.get

        # Проверяем через getattr, т.к. __getattribute__ перехватывает прямой доступ
        assert proxy.method == "POST"
        assert proxy.base_url == "https://base.com"
        assert proxy.url == "/path"
        assert proxy.params == {"q": "1"}
        assert proxy.headers["X-Custom"] == "val"
        assert proxy.body == {}
        assert proxy.retries == 3

    def test_sec_headers_hides_authorization(self):
        """sec_headers маскирует Authorization."""
        req = FluentReq()
        req.headers({"Authorization": "Bearer secret123", "X-Api-Key": "key456"})
        proxy = req.get

        secured = proxy.sec_headers
        assert secured["Authorization"] == "***"
        assert secured["X-Api-Key"] == "key456"

    def test_sec_headers_hides_lowercase_authorization(self):
        """sec_headers маскирует authorization (нижний регистр)."""
        req = FluentReq()
        req.headers({"authorization": "token abc"})
        proxy = req.get

        assert proxy.sec_headers["authorization"] == "***"

    def test_sec_headers_returns_copy(self):
        """sec_headers не модифицирует оригинальный headers."""
        req = FluentReq()
        req.headers({"Authorization": "Bearer secret"})
        proxy = req.get

        _ = proxy.sec_headers
        assert getattr(proxy, "headers")["Authorization"] == "Bearer secret"


# ═══════════════════════════════════════════════════════════════════════════════
# FluentRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestFluentRequest:
    """Тесты для FluentRequest — builder для HTTP-запроса."""

    def test_default_values(self):
        """FluentRequest создаётся с дефолтными значениями (через .get)."""
        req = FluentReq()
        proxy = req.get

        assert getattr(proxy, "method") == "GET"
        assert getattr(proxy, "base_url") is None
        assert getattr(proxy, "url") == ""
        assert getattr(proxy, "params") == {}
        assert getattr(proxy, "headers") == {"Content-Type": "application/json", "Accept": "application/json"}
        assert getattr(proxy, "cookies") == {}
        assert getattr(proxy, "body") == {}
        assert getattr(proxy, "retries") == 3

    def test_method_fluent(self):
        """method() устанавливает HTTP-метод и возвращает self."""
        req = FluentReq()
        result = req.method("POST")
        assert getattr(req.get, "method") == "POST"
        assert result is req

    def test_base_url_fluent(self):
        """base_url() устанавливает базовый URL."""
        req = FluentReq()
        req.base_url("https://api.example.com")
        assert getattr(req.get, "base_url") == "https://api.example.com"

    def test_url_fluent(self):
        """url() устанавливает путь."""
        req = FluentReq()
        req.url("/v1/users")
        assert getattr(req.get, "url") == "/v1/users"

    def test_params_fluent(self):
        """params() добавляет параметры запроса."""
        req = FluentReq()
        req.params({"key1": "val1"})
        req.params({"key2": "val2"})
        assert getattr(req.get, "params") == {"key1": "val1", "key2": "val2"}

    def test_headers_fluent(self):
        """headers() добавляет заголовки."""
        req = FluentReq()
        req.headers({"Content-Type": "text/plain"})
        assert getattr(req.get, "headers")["Content-Type"] == "text/plain"

    def test_cookies_fluent(self):
        """cookies() добавляет куки."""
        req = FluentReq()
        req.cookies({"session": "abc123"})
        assert getattr(req.get, "cookies") == {"session": "abc123"}

    def test_body_fluent(self):
        """body() добавляет поля в тело запроса."""
        req = FluentReq()
        req.body({"name": "John"})
        req.body({"age": 30})
        assert getattr(req.get, "body") == {"name": "John", "age": 30}

    def test_retries_fluent(self):
        """retries() устанавливает количество ретраев."""
        req = FluentReq()
        req.retries(5)
        assert getattr(req.get, "retries") == 5

    def test_reload_scripts(self):
        """reload_scripts() сбрасывает флаг выполнения before-скриптов."""
        req = FluentReq()
        req.reload_scripts()
        assert req._before_scripts_done is False

    def test_script_before(self):
        """script() с typ='before' добавляет скрипт в before_scripts."""
        req = FluentReq()
        req.script("params['key'] = 'val'", typ="before")
        assert req._before_scripts == ["params['key'] = 'val'"]
        assert req._before_scripts_done is False

    def test_script_after(self):
        """script() с typ='after' добавляет скрипт в after_scripts."""
        req = FluentReq()
        req.script("body['result'] = 'ok'", typ="after")
        assert req._after_scripts == ["body['result'] = 'ok'"]

    def test_copy_creates_independent_instance(self):
        """copy() создаёт независимую копию FluentRequest."""
        req = FluentReq("https://base.com")
        req.method("POST").url("/path").params({"q": "1"}).headers({"X-ID": "123"})
        req.cookies({"s": "tok"}).body({"data": 1}).retries(5)
        req.script("before_script", typ="before")
        req.script("after_script", typ="after")

        copied = req.copy()

        # Значения совпадают
        assert getattr(copied.get, "method") == "POST"
        assert getattr(copied.get, "base_url") == "https://base.com"
        assert getattr(copied.get, "url") == "/path"
        assert getattr(copied.get, "params") == {"q": "1"}
        assert getattr(copied.get, "headers")["X-ID"] == "123"
        assert getattr(copied.get, "cookies") == {"s": "tok"}
        assert getattr(copied.get, "body") == {"data": 1}
        assert getattr(copied.get, "retries") == 5
        assert copied._before_scripts == ["before_script"]
        assert copied._after_scripts == ["after_script"]

        # Изменение копии не влияет на оригинал
        copied.method("GET").url("/other")
        assert getattr(req.get, "method") == "POST"
        assert getattr(req.get, "url") == "/path"

    @pytest.mark.asyncio
    async def test_execute_without_client_creates_new(self):
        """execute() без клиента создаёт временный AsyncClient."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")

        with patch("src.magutils.http.request.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            MockClient.return_value = mock_client

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.is_success = True
            mock_client.request = AsyncMock(return_value=mock_response)

            resp = await req.execute()

            assert resp is mock_response
            MockClient.assert_called_once_with(base_url="https://httpbin.org")
            mock_client.request.assert_awaited_once_with(
                "GET", "/get", data=None, params={},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                cookies={}
            )

    @pytest.mark.asyncio
    async def test_execute_with_client(self):
        """execute() с переданным клиентом использует его."""
        req = FluentReq("https://httpbin.org")
        req.method("POST").url("/post").body({"key": "value"})

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_client.request = AsyncMock(return_value=mock_response)

        resp = await req.execute(mock_client)

        assert resp is mock_response
        mock_client.request.assert_awaited_once()
        call_kwargs = mock_client.request.await_args[1]
        assert call_kwargs["data"] == orjson.dumps({"key": "value"})

    @pytest.mark.asyncio
    async def test_execute_serializes_body_once(self):
        """__execute сериализует body в _serialized_body только один раз."""
        req = FluentReq("https://httpbin.org")
        req.method("POST").url("/post").body({"key": "value"})

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_client.request = AsyncMock(return_value=mock_response)

        await req.execute(mock_client)
        first_serialized = req._serialized_body

        # Повторный вызов — сериализация не происходит заново
        await req.execute(mock_client)
        assert req._serialized_body is first_serialized

    @pytest.mark.asyncio
    async def test_execute_runs_before_scripts(self):
        """__execute выполняет before-скрипты перед запросом."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")
        req.script("params['from_script'] = 'yes'", typ="before")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("src.magutils.http.request.QHookRunner.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ({"from_script": "yes"}, {}, {})
            await req.execute(mock_client)

        mock_run.assert_called_once()
        assert req._before_scripts_done is True

    @pytest.mark.asyncio
    async def test_execute_runs_after_scripts_on_success(self):
        """__execute выполняет after-скрипты при успешном ответе."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")
        req.script("body['processed'] = True", typ="after")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        # Используем настоящий Response вместо MagicMock, чтобы headers работал
        real_response = httpx.Response(200, content=orjson.dumps({"original": "data"}))
        mock_client.request = AsyncMock(return_value=real_response)

        with patch("src.magutils.http.request.QHookRunner.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ({}, {}, {"original": "data", "processed": True})
            resp = await req.execute(mock_client)

        assert resp.status_code == 200
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_skips_after_scripts_on_error(self):
        """__execute НЕ выполняет after-скрипты при ошибке ответа."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")
        req.script("body['processed'] = True", typ="after")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("src.magutils.http.request.QHookRunner.run", new_callable=AsyncMock) as mock_run:
            resp = await req.execute(mock_client)

        assert resp.status_code == 500
        mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_execute_scripts_without_body(self):
        """Скрипты НЕ выполняются без тела ответа."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")
        req.script("body['processed'] = True", typ="after")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.content = b'not json'
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("src.magutils.http.request.QHookRunner.run", new_callable=AsyncMock) as mock_run:
            resp = await req.execute(mock_client)

        assert resp.status_code == 200
        mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_before_scripts_run_once_by_default(self):
        """before-скрипты выполняются только один раз при множественных execute."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")
        req.script("params['ts'] = 'now'", typ="before")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("src.magutils.http.request.QHookRunner.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ({"ts": "now"}, {}, {})
            await req.execute(mock_client)
            await req.execute(mock_client)

        assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_reload_scripts_allows_rerun(self):
        """reload_scripts() позволяет выполнить before-скрипты снова."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")
        req.script("params['ts'] = 'now'", typ="before")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("src.magutils.http.request.QHookRunner.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ({"ts": "now"}, {}, {})
            await req.execute(mock_client)
            req.reload_scripts()
            await req.execute(mock_client)

        assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_concurrent_safety(self):
        """Параллельные execute не вызывают состояние гонки благодаря Lock."""
        req = FluentReq("https://httpbin.org")
        req.method("GET").url("/get")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_client.request = AsyncMock(return_value=mock_response)

        async def execute_and_check():
            return await req.execute(mock_client)

        results = await asyncio.gather(execute_and_check(), execute_and_check())
        assert len(results) == 2
        assert all(r is mock_response for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers: Storage
# ═══════════════════════════════════════════════════════════════════════════════

class TestStorage:
    """Тесты для Storage — простое key-value хранилище."""

    def test_save_and_load(self):
        """save() сохраняет значение, load() его возвращает."""
        storage = Storage()
        storage.save("key1", "value1")
        assert storage.load("key1") == "value1"

    def test_load_default(self):
        """load() возвращает default для отсутствующего ключа."""
        storage = Storage()
        assert storage.load("nonexistent", "fallback") == "fallback"

    def test_load_none_default(self):
        """load() возвращает None для отсутствующего ключа без default."""
        storage = Storage()
        assert storage.load("nonexistent") is None

    def test_overwrite(self):
        """save() перезаписывает существующее значение."""
        storage = Storage()
        storage.save("key", "old")
        storage.save("key", "new")
        assert storage.load("key") == "new"


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers: QHookRunner
# ═══════════════════════════════════════════════════════════════════════════════

class TestQHookRunner:
    """Тесты для QHookRunner — запуск Starlark-хуков."""

    @pytest.mark.asyncio
    async def test_run_modifies_params(self):
        """run() позволяет скрипту модифицировать params."""
        params, headers, body = await QHookRunner.run(
            "params['x'] = 42",
            {"a": 1},
            {"Content-Type": "application/json"},
            {"data": "test"},
        )
        assert params == {"a": 1, "x": 42}

    @pytest.mark.asyncio
    async def test_run_modifies_headers(self):
        """run() позволяет скрипту модифицировать headers."""
        params, headers, body = await QHookRunner.run(
            "headers['X-Custom'] = 'yes'",
            {},
            {},
            {},
        )
        assert headers == {"X-Custom": "yes"}

    @pytest.mark.asyncio
    async def test_run_modifies_body(self):
        """run() позволяет скрипту модифицировать body."""
        params, headers, body = await QHookRunner.run(
            "body['processed'] = True",
            {},
            {},
            {"original": "data"},
        )
        assert body == {"original": "data", "processed": True}

    @pytest.mark.asyncio
    async def test_run_returns_tuple(self):
        """run() возвращает кортеж (params, headers, body)."""
        result = await QHookRunner.run(
            "params['p'] = 1\nheaders['h'] = '2'\nbody['b'] = 3",
            {},
            {},
            {},
        )
        assert isinstance(result, tuple)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_run_with_storage(self):
        """run() с storage позволяет сохранять и загружать данные между вызовами."""
        storage = Storage()
        runner = QHookRunner(storage=storage)

        await QHookRunner.run(
            "st_save('token', 'abc123')",
            {}, {}, {},
            wrapper=runner.wrap_template,
        )
        params, headers, body = await QHookRunner.run(
            "body['saved_token'] = st_load('token')",
            {}, {}, {},
            wrapper=runner.wrap_template,
        )
        assert body == {"saved_token": "abc123"}

    @pytest.mark.asyncio
    async def test_run_empty_script(self):
        """run() с пустым скриптом не меняет входные данные."""
        params, headers, body = await QHookRunner.run(
            "",
            {"p": 1},
            {"h": "v"},
            {"b": 2},
        )
        assert params == {"p": 1}
        assert headers == {"h": "v"}
        assert body == {"b": 2}

    @pytest.mark.asyncio
    async def test_run_script_error_raises(self):
        """run() пробрасывает исключение при ошибке в скрипте."""
        with pytest.raises(Exception):
            await QHookRunner.run(
                "raise('error')",
                {}, {}, {},
            )


import asyncio