import asyncio
import logging
import warnings

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from magutils.pipeline import Pipeline, step, PipeCTX

# Игнорируем предупреждение о never-awaited корутинах,
# т.к. при раннем выходе из пайплайна last_step() может быть не вызван
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine 'Pipeline.last_step' was never awaited:RuntimeWarning"
)


@pytest.fixture(autouse=True)
def _patch_pipeline_logger():
    """Отключаем вывод логов пайплайна в тестах."""
    logger = logging.getLogger('magutils.pipeline.base')
    logger.setLevel(logging.CRITICAL + 1)  # выше CRITICAL — ничего не пишет
    yield
    logger.setLevel(logging.NOTSET)  # восстанавливаем после теста


class TestPipeCTX:
    """Тесты для класса PipeCTX."""

    def test_init_without_kwargs(self):
        """Тест создания контекста без аргументов."""
        ctx = PipeCTX()
        assert ctx.id is not None
        assert isinstance(ctx.id, str)
        assert ctx.kwargs == {}

    def test_init_with_kwargs(self):
        """Тест создания контекста с аргументами."""
        ctx = PipeCTX(user_id=42, role="admin")
        assert ctx.id is not None
        assert ctx.kwargs == {"user_id": 42, "role": "admin"}

    def test_unique_ids(self):
        """Тест уникальности ID."""
        ctx1 = PipeCTX()
        ctx2 = PipeCTX()
        assert ctx1.id != ctx2.id


class TestPipelineMeta:
    """Тесты для мета-класса PipelineMeta."""

    def test_steps_collected_in_order(self):
        """Тест, что шаги собираются и сортируются по order."""

        class TestPipeline(Pipeline):
            @step(order=3)
            async def step_c(self):
                ...

            @step(order=1)
            async def step_a(self):
                ...

            @step(order=2)
            async def step_b(self):
                ...

        steps = TestPipeline._steps
        assert len(steps) == 3
        assert steps[0] == ("step_a", 1)
        assert steps[1] == ("step_b", 2)
        assert steps[2] == ("step_c", 3)

    def test_no_steps(self):
        """Тест пайплайна без шагов."""

        class EmptyPipeline(Pipeline):
            pass

        assert EmptyPipeline._steps == []

    def test_regular_methods_not_collected(self):
        """Тест, что обычные методы не попадают в шаги."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                ...

            async def not_a_step(self):
                pass

            def also_not_a_step(self):
                pass

        steps = TestPipeline._steps
        assert len(steps) == 1
        assert steps[0] == ("step_a", 1)

    def test_step_on_callable_raises_type_error(self):
        """Тест, что @step на callable-объекте (не функции) вызывает TypeError."""

        class CallableObject:
            __name__ = 'test'

            def __call__(self):
                pass

        with pytest.raises(TypeError, match="Unknown function type!"):
            # Пытаемся применить декоратор step к экземпляру callable-класса
            step(1)(CallableObject())


class TestPipeline:
    """Тесты для класса Pipeline."""

    @pytest.mark.asyncio
    async def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию."""
        pipeline = Pipeline()
        assert pipeline.result is None
        assert pipeline.step_num == 0
        assert pipeline.step_name is None
        assert isinstance(pipeline.ctx, PipeCTX)

    @pytest.mark.asyncio
    async def test_init_with_custom_ctx(self):
        """Тест инициализации с кастомной фабрикой контекста."""

        class CustomCTX(PipeCTX):
            pass

        pipeline = Pipeline(ctx_factory=CustomCTX)
        assert isinstance(pipeline.ctx, CustomCTX)

    @pytest.mark.asyncio
    async def test_name_property(self):
        """Тест свойства name."""
        pipeline = Pipeline()
        expected = f"Pipeline<{pipeline.ctx.id}>"
        assert pipeline.name == expected

    @pytest.mark.asyncio
    async def test_get_steps(self):
        """Тест метода get_steps."""

        class TestPipeline(Pipeline):
            @step(order=2)
            async def step_b(self):
                ...

            @step(order=1)
            async def step_a(self):
                ...

        pipeline = TestPipeline()
        steps = pipeline.get_steps()
        assert steps == [("step_a", 1), ("step_b", 2)]

    @pytest.mark.asyncio
    async def test_last_step_returns_none(self):
        """Тест, что last_step возвращает None."""
        pipeline = Pipeline()
        result = await pipeline.last_step()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_empty_pipeline_raises_error(self):
        """Тест, что запуск пайплайна без шагов вызывает ошибку."""

        class EmptyPipeline(Pipeline):
            pass

        with pytest.raises(RuntimeError, match="No steps assigned"):
            await EmptyPipeline.run()

    # ──────────────────────────────────────────────
    # Асинхронные шаги (async def)
    # ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_async_steps_execute_in_order(self):
        """Тест выполнения асинхронных шагов по порядку."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("step_a")

            @step(order=2)
            async def step_b(self):
                execution_order.append("step_b")

            @step(order=3)
            async def step_c(self):
                execution_order.append("step_c")

        await TestPipeline.run()
        assert execution_order == ["step_a", "step_b", "step_c"]

    @pytest.mark.asyncio
    async def test_async_step_early_exit_on_return(self):
        """Тест раннего выхода при return не-None в async шаге."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("step_a")
                return {"from": "step_a"}

            @step(order=2)
            async def step_b(self):
                execution_order.append("step_b")

        await TestPipeline.run()
        assert execution_order == ["step_a"]

    @pytest.mark.asyncio
    async def test_async_step_early_exit_sets_result(self):
        """Тест, что ранний выход устанавливает result."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                return {"from": "step_a"}

            @step(order=2)
            async def step_b(self):
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert result.result == {"from": "step_a"}

    @pytest.mark.asyncio
    async def test_async_step_early_exit_on_middle_step(self):
        """Тест раннего выхода на среднем async шаге."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("step_a")

            @step(order=2)
            async def step_b(self):
                execution_order.append("step_b")
                return {"from": "step_b"}

            @step(order=3)
            async def step_c(self):
                execution_order.append("step_c")

        await TestPipeline.run()
        assert execution_order == ["step_a", "step_b"]

    @pytest.mark.asyncio
    async def test_async_step_return_none_continues(self):
        """Тест, что return None в async шаге не вызывает ранний выход."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                return None  # явный None — не ранний выход

            @step(order=2)
            async def step_b(self):
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert result.result == {"from": "step_b"}

    @pytest.mark.asyncio
    async def test_async_step_implicit_none_continues(self):
        """Тест, что неявный None (без return) в async шаге не вызывает ранний выход."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                pass  # неявный return None

            @step(order=2)
            async def step_b(self):
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert result.result == {"from": "step_b"}

    @pytest.mark.asyncio
    async def test_async_step_raises_exception(self):
        """Тест, что исключение в async шаге пробрасывается."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await TestPipeline.run()

    @pytest.mark.asyncio
    async def test_async_step_after_exception_not_executed(self):
        """Тест, что шаги после исключения не выполняются."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("step_a")
                raise RuntimeError("fail")

            @step(order=2)
            async def step_b(self):
                execution_order.append("step_b")

        with pytest.raises(RuntimeError):
            await TestPipeline.run()
        assert execution_order == ["step_a"]

    # ──────────────────────────────────────────────
    # Синхронные шаги (def)
    # ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_sync_steps_execute_in_order(self):
        """Тест выполнения синхронных шагов по порядку."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                execution_order.append("step_a")

            @step(order=2)
            def step_b(self):
                execution_order.append("step_b")

            @step(order=3)
            def step_c(self):
                execution_order.append("step_c")

        await TestPipeline.run()
        assert execution_order == ["step_a", "step_b", "step_c"]

    @pytest.mark.asyncio
    async def test_sync_step_early_exit_on_return(self):
        """Тест раннего выхода при return не-None в синхронном шаге."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                execution_order.append("step_a")
                return {"from": "step_a"}

            @step(order=2)
            def step_b(self):
                execution_order.append("step_b")

        await TestPipeline.run()
        assert execution_order == ["step_a"]

    @pytest.mark.asyncio
    async def test_sync_step_early_exit_sets_result(self):
        """Тест, что ранний выход устанавливает result в синхронном шаге."""

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                return {"from": "step_a"}

            @step(order=2)
            def step_b(self):
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert result.result == {"from": "step_a"}

    @pytest.mark.asyncio
    async def test_sync_step_return_none_continues(self):
        """Тест, что return None в синхронном шаге не вызывает ранний выход."""

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                return None

            @step(order=2)
            def step_b(self):
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert result.result == {"from": "step_b"}

    @pytest.mark.asyncio
    async def test_sync_step_implicit_none_continues(self):
        """Тест, что неявный None в синхронном шаге не вызывает ранний выход."""

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                pass

            @step(order=2)
            def step_b(self):
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert result.result == {"from": "step_b"}

    @pytest.mark.asyncio
    async def test_sync_step_raises_exception(self):
        """Тест, что исключение в синхронном шаге пробрасывается."""

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                raise ValueError("sync error")

        with pytest.raises(ValueError, match="sync error"):
            await TestPipeline.run()

    # ──────────────────────────────────────────────
    # Асинхронные генераторы (async def с yield)
    # ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_async_gen_yield_continues_to_next_step(self):
        """Тест, что yield в async генераторе передаёт управление дальше."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("step_a before yield")
                yield
                execution_order.append("step_a after yield")

            @step(order=2)
            async def step_b(self):
                execution_order.append("step_b")

        await TestPipeline.run()
        assert execution_order == [
            "step_a before yield",
            "step_b",
            "step_a after yield",
        ]

    @pytest.mark.asyncio
    async def test_async_gen_yield_chain(self):
        """Тест цепочки yield через несколько шагов."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("a enter")
                yield
                execution_order.append("a exit")

            @step(order=2)
            async def step_b(self):
                execution_order.append("b enter")
                yield
                execution_order.append("b exit")

            @step(order=3)
            async def step_c(self):
                execution_order.append("c enter")
                yield
                execution_order.append("c exit")

        await TestPipeline.run()
        assert execution_order == [
            "a enter",
            "b enter",
            "c enter",
            "c exit",
            "b exit",
            "a exit",
        ]

    @pytest.mark.asyncio
    async def test_async_gen_early_exit_in_next_step(self):
        """Тест, что ранний выход в шаге после yield-шага работает корректно."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("a enter")
                yield
                execution_order.append("a exit")

            @step(order=2)
            async def step_b(self):
                execution_order.append("b")
                return {"from": "b"}  # ранний выход

            @step(order=3)
            async def step_c(self):
                execution_order.append("c")

        result = await TestPipeline.run()
        assert execution_order == ["a enter", "b", "a exit"]
        assert result.result == {"from": "b"}

    # ──────────────────────────────────────────────
    # Синхронные генераторы (def с yield)
    # ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_sync_gen_yield_continues_to_next_step(self):
        """Тест, что yield в синхронном генераторе передаёт управление дальше."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                execution_order.append("step_a before yield")
                yield
                execution_order.append("step_a after yield")

            @step(order=2)
            def step_b(self):
                execution_order.append("step_b")

        await TestPipeline.run()
        assert execution_order == [
            "step_a before yield",
            "step_b",
            "step_a after yield",
        ]

    @pytest.mark.asyncio
    async def test_sync_gen_yield_chain(self):
        """Тест цепочки yield через несколько синхронных шагов."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                execution_order.append("a enter")
                yield
                execution_order.append("a exit")

            @step(order=2)
            def step_b(self):
                execution_order.append("b enter")
                yield
                execution_order.append("b exit")

            @step(order=3)
            def step_c(self):
                execution_order.append("c enter")
                yield
                execution_order.append("c exit")

        await TestPipeline.run()
        assert execution_order == [
            "a enter",
            "b enter",
            "c enter",
            "c exit",
            "b exit",
            "a exit",
        ]

    @pytest.mark.asyncio
    async def test_sync_gen_early_exit_in_next_step(self):
        """Тест, что ранний выход в шаге после sync yield-шага работает корректно."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            def step_a(self):
                execution_order.append("a enter")
                yield
                execution_order.append("a exit")

            @step(order=2)
            def step_b(self):
                execution_order.append("b")
                return {"from": "b"}  # ранний выход

            @step(order=3)
            def step_c(self):
                execution_order.append("c")

        result = await TestPipeline.run()
        assert execution_order == ["a enter", "b", "a exit"]
        assert result.result == {"from": "b"}

    # ──────────────────────────────────────────────
    # Смешанные типы шагов
    # ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_mixed_async_and_sync_steps(self):
        """Тест смешанных async и sync шагов."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("async a")

            @step(order=2)
            def step_b(self):
                execution_order.append("sync b")

            @step(order=3)
            async def step_c(self):
                execution_order.append("async c")

        await TestPipeline.run()
        assert execution_order == ["async a", "sync b", "async c"]

    @pytest.mark.asyncio
    async def test_mixed_async_gen_and_sync_gen(self):
        """Тест смешанных async генераторов и sync генераторов."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                execution_order.append("async a enter")
                yield
                execution_order.append("async a exit")

            @step(order=2)
            def step_b(self):
                execution_order.append("sync b enter")
                yield
                execution_order.append("sync b exit")

            @step(order=3)
            async def step_c(self):
                execution_order.append("async c enter")
                yield
                execution_order.append("async c exit")

        await TestPipeline.run()
        assert execution_order == [
            "async a enter",
            "sync b enter",
            "async c enter",
            "async c exit",
            "sync b exit",
            "async a exit",
        ]

    # ──────────────────────────────────────────────
    # Контекст и result
    # ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_run_returns_self(self):
        """Тест, что run возвращает экземпляр пайплайна."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                ...

        result = await TestPipeline.run()
        assert isinstance(result, TestPipeline)

    @pytest.mark.asyncio
    async def test_step_can_access_ctx(self):
        """Тест доступа к контексту из шага."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                return {"ctx_id": self.ctx.id}

        result = await TestPipeline.run()
        assert "ctx_id" in result.result
        assert isinstance(result.result["ctx_id"], str)

    @pytest.mark.asyncio
    async def test_multiple_runs_produce_different_contexts(self):
        """Тест, что разные запуски имеют разные контексты."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                return {"ctx_id": self.ctx.id}

        result1 = await TestPipeline.run()
        result2 = await TestPipeline.run()
        assert result1.result["ctx_id"] != result2.result["ctx_id"]

    @pytest.mark.asyncio
    async def test_run_with_custom_context(self):
        """Тест запуска с кастомным контекстом."""

        class CustomCTX(PipeCTX):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.user_id = kwargs.get("user_id")

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                return {"user_id": self.ctx.user_id}

        result = await TestPipeline.run(ctx_factory=CustomCTX, user_id=42)
        assert result.result == {"user_id": 42}

    @pytest.mark.asyncio
    async def test_step_num_and_name_set(self):
        """Тест, что step_num и step_name устанавливаются корректно."""
        step_info = {}

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                step_info["step_a"] = (self.step_num, self.step_name)

            @step(order=2)
            async def step_b(self):
                step_info["step_b"] = (self.step_num, self.step_name)

        await TestPipeline.run()
        assert step_info["step_a"] == (1, "step_a")
        assert step_info["step_b"] == (2, "step_b")

    @pytest.mark.asyncio
    async def test_first_result_wins(self):
        """Тест, что учитывается только первый результат."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                return {"from": "step_a"}

            @step(order=2)
            async def step_b(self):
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert result.result == {"from": "step_a"}

    @pytest.mark.asyncio
    async def test_result_none_when_no_step_returns_value(self):
        """Тест, что result остаётся None, если ни один шаг ничего не вернул."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self):
                ...

            @step(order=2)
            async def step_b(self):
                ...

        result = await TestPipeline.run()
        assert result.result is None