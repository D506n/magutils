import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from starlark import StarlarkError
from magutils.star.starlark import (
    StarResult,
    BaseCTX,
    Runner,
    DEFAULT_WRAPPER,
    REGEX_CACHE,
)


class TestStarResult:
    """Тесты для класса StarResult."""

    def test_initial_state(self):
        """Тест начального состояния."""
        res = StarResult()
        assert res.success is False
        assert res.prints == []
        assert res._res is None
        assert res._error is None

    def test_result_setter_success(self):
        """Тест установки результата."""
        res = StarResult()
        res.result = {"foo": "bar"}
        assert res.success is True
        assert res._res == {"foo": "bar"}

    def test_result_getter_success(self):
        """Тест получения результата при успехе."""
        res = StarResult()
        res.result = {"foo": "bar"}
        assert res.result == {"foo": "bar"}

    def test_result_getter_failure(self):
        """Тест получения результата при ошибке."""
        res = StarResult()
        res.error = ValueError("test error")
        with pytest.raises(ValueError, match="test error"):
            _ = res.result

    def test_error_setter(self):
        """Тест установки ошибки."""
        res = StarResult()
        res.error = RuntimeError("something went wrong")
        assert res.success is False
        assert isinstance(res._error, RuntimeError)

    def test_error_getter(self):
        """Тест получения ошибки."""
        res = StarResult()
        res.error = KeyError("missing")
        with pytest.raises(KeyError, match="missing"):
            _ = res.error


class TestSTCtx:
    """Тесты для класса STCtx."""

    def test_init(self):
        """Тест инициализации контекста."""
        ctx = BaseCTX()
        assert ctx.prints == []
        assert ctx.mod["results"] == {}
        assert ctx.mod["input"] == {}

    def test_print(self):
        """Тест функции print."""
        ctx = BaseCTX()
        ctx.print("hello", "world")
        assert ctx.prints == ["hello", "world"]
        ctx.print(42)
        assert ctx.prints == ["hello", "world", "42"]

    def test_re_search(self):
        """Тест функции re_search."""
        ctx = BaseCTX()
        # Первый вызов компилирует паттерн
        result = ctx.re_search(r"\d+", "abc123def", 0)
        assert result == "123"
        # Проверяем кэш
        assert r"\d+" in REGEX_CACHE
        # Группа
        result = ctx.re_search(r"(\d+)(\w+)", "123abc", 1)
        assert result == "123"
        # Не найдено
        result = ctx.re_search(r"\d+", "abcdef", 0)
        assert result is None

    def test_clear(self):
        """Тест очистки контекста."""
        ctx = BaseCTX()
        ctx.mod["results"] = {"a": 1}
        ctx.mod["input"] = {"b": 2}
        ctx.prints.append("test")
        ctx.clear()
        assert ctx.mod["results"] == {}
        assert ctx.mod["input"] == {}
        assert ctx.prints == []


class TestRunner:
    """Тесты для класса Runner."""

    def test_init(self):
        """Тест инициализации Runner."""
        runner = Runner(size=3)
        assert runner.ctxs.qsize() == 3
        assert runner.wrapper == DEFAULT_WRAPPER

    def test_wrap_script(self):
        """Тест обёртки скрипта."""
        runner = Runner()
        script = "return input"
        wrapped = runner.wrap_script(script)
        assert "def process(input):" in wrapped
        assert "   return input" in wrapped
        # Кэширование
        wrapped2 = runner.wrap_script(script)
        assert wrapped == wrapped2

    def test_parse(self):
        """Тест парсинга скрипта."""
        runner = Runner()
        script = "def foo(): return 1"
        ast = runner.parse(script)
        assert ast is not None
        # Кэширование
        ast2 = runner.parse(script)
        assert ast == ast2

    @pytest.mark.asyncio
    async def test_get_ctx(self):
        """Тест получения контекста."""
        runner = Runner(size=1)
        async with runner.get_ctx() as ctx:
            assert isinstance(ctx, BaseCTX)
        # Контекст возвращается в очередь
        assert runner.ctxs.qsize() == 1

    @pytest.mark.asyncio
    async def test_run_basic(self):
        """Тест выполнения простого скрипта."""
        script = "return input['x']"
        data = {"x": 42}
        result = await Runner.run(script, data)
        assert result.success is True
        assert result.result == {"result": 42}
        assert result.prints == []

    @pytest.mark.asyncio
    async def test_run_with_print(self):
        """Тест скрипта с выводом."""
        script = """
print("hello")
print("world")
return input
"""
        data = {}
        result = await Runner.run(script, data)
        assert result.success is True
        assert result.prints == ["hello", "world"]

    @pytest.mark.asyncio
    async def test_run_dict_result(self):
        """Тест возврата словаря."""
        script = "return {'answer': 42}"
        result = await Runner.run(script, {})
        assert result.success is True
        assert result.result == {"answer": 42}

    @pytest.mark.asyncio
    async def test_run_list_result(self):
        """Тест возврата списка."""
        script = "return [1, 2, 3]"
        result = await Runner.run(script, {})
        assert result.success is True
        assert result.result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_run_none_result(self):
        """Тест возврата None."""
        script = "return None"
        result = await Runner.run(script, {})
        assert result.success is True
        assert result.result == {}

    @pytest.mark.asyncio
    async def test_run_error(self):
        """Тест ошибки в скрипте."""
        script = "1/0"
        result = await Runner.run(script, {})
        assert result.success is False
        with pytest.raises(StarlarkError, match="1/0"):
            _ = result.result

    @pytest.mark.asyncio
    async def test_run_with_regex(self):
        """Тест использования regex функций."""
        script = """
match = re.search(r'\\d+', 'abc123def')
return {'match': match}
"""
        result = await Runner.run(script, {})
        assert result.success is True
        assert result.result == {"match": "123"}

    @pytest.mark.asyncio
    async def test_run_with_time(self):
        """Тест использования time."""
        script = """
t = time.now()
return {'time': t}
"""
        result = await Runner.run(script, {})
        assert result.success is True
        assert isinstance(result.result['time'], (int, float))

    @pytest.mark.asyncio
    async def test_run_with_json(self):
        """Тест использования JSON (библиотека доступна через globs)."""
        script = """
data = json.encode({'foo': 'bar'})
return {'encoded': data}
"""
        result = await Runner.run(script, {})
        # starlark-pyo3 предоставляет json.encode/decode
        assert result.success is True
        assert result.result['encoded'] == '{"foo":"bar"}'

    @pytest.mark.asyncio
    async def test_inst_singleton(self):
        """Тест синглтон-инстанса Runner."""
        runner1 = Runner.inst()
        runner2 = Runner.inst()
        assert runner1 is runner2
        # С другим wrapper'ом создаётся новый инстанс
        custom_wrapper = "def process(input):\n    return input"
        runner3 = Runner.inst(custom_wrapper)
        runner4 = Runner.inst(custom_wrapper)
        assert runner3 is runner4
        assert runner3 is not runner1

    @pytest.mark.asyncio
    async def test_custom_wrapper(self):
        """Тест пользовательского wrapper'а."""
        custom_wrapper = """
def process(input):
{script}

def main(inp):
    result = process(inp)
    return {{'custom': result}}

results = main(input)
"""
        script = "return input * 2"
        data = 5
        result = await Runner.run(script, data, wrapper=custom_wrapper)
        assert result.success is True
        assert result.result == {"custom": 10}