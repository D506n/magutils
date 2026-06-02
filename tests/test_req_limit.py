import asyncio

import pytest
from aiolimiter import AsyncLimiter

from src.magutils.req_limit import Limiter


@pytest.fixture
def reset_limiter():
    """Фикстура для сброса синглтона Limiter между тестами."""
    Limiter._Limiter__inst = None
    yield
    Limiter._Limiter__inst = None


class TestLimiter:
    """Тесты для класса Limiter — синглтон с асинхронным rate limiter."""

    def test_singleton_returns_same_instance(self, reset_limiter):
        """inst() возвращает тот же экземпляр при повторных вызовах."""
        instance1 = Limiter.inst()
        instance2 = Limiter.inst()

        assert instance1 is instance2

    def test_set_creates_limiter_with_params(self, reset_limiter):
        """set() создаёт лимитер с указанными параметрами."""
        Limiter.set("test_key", limit=5, per=2)

        limiter = Limiter.get("test_key")
        assert isinstance(limiter, AsyncLimiter)
        assert limiter.max_rate == 5
        assert limiter.time_period == 2

    def test_get_returns_existing_limiter(self, reset_limiter):
        """get() возвращает существующий лимитер."""
        Limiter.set("test_key", limit=10, per=1)

        limiter1 = Limiter.get("test_key")
        limiter2 = Limiter.get("test_key")

        assert limiter1 is limiter2

    def test_get_creates_limiter_with_defaults(self, reset_limiter):
        """get() создаёт лимитер с дефолтными параметрами, если ключа нет."""
        limiter = Limiter.get("nonexistent_key")

        assert isinstance(limiter, AsyncLimiter)
        assert limiter.max_rate == 10
        assert limiter.time_period == 1

    @pytest.mark.asyncio
    async def test_rate_limit_passes_within_limit(self, reset_limiter):
        """rate_limit пропускает запросы в пределах лимита."""
        Limiter.set("test_key", limit=5, per=1)

        for _ in range(5):
            async with Limiter.rate_limit("test_key"):
                pass  # Все 5 запросов должны пройти без ожидания

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_when_exceeded(self, reset_limiter):
        """rate_limit приостанавливает выполнение при превышении лимита."""
        Limiter.set("test_key", limit=1, per=1)

        # Первый запрос проходит мгновенно
        async with Limiter.rate_limit("test_key"):
            pass

        # Второй запрос должен заблокироваться — замеряем время выполнения
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.05):
                async with Limiter.rate_limit("test_key"):
                    pass

    @pytest.mark.asyncio
    async def test_different_keys_do_not_interfere(self, reset_limiter):
        """Разные ключи не влияют друг на друга."""
        Limiter.set("key_a", limit=1, per=1)
        Limiter.set("key_b", limit=10, per=1)

        # Исчерпываем лимит key_a
        async with Limiter.rate_limit("key_a"):
            pass

        # key_b должен продолжать пропускать запросы
        for _ in range(10):
            async with Limiter.rate_limit("key_b"):
                pass

    @pytest.mark.asyncio
    async def test_rate_limit_works_as_context_manager(self, reset_limiter):
        """rate_limit корректно работает как асинхронный контекстный менеджер."""
        Limiter.set("test_key", limit=10, per=1)

        async with Limiter.rate_limit("test_key") as result:
            assert result is None  # Контекстный менеджер ничего не возвращает