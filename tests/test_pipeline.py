import asyncio
import warnings

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from magutils.pipeline import Pipeline, step, PipeCTX

# Игнорируем предупреждение о never-awaited корутинах,
# т.к. при раннем выходе из пайплайна last_step() может быть не вызван
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine 'Pipeline.last_step' was never awaited:RuntimeWarning"
)


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
            async def step_c(self, call_next):
                return await call_next

            @step(order=1)
            async def step_a(self, call_next):
                return await call_next

            @step(order=2)
            async def step_b(self, call_next):
                return await call_next

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
            async def step_a(self, call_next):
                return await call_next

            async def not_a_step(self):
                pass

            def also_not_a_step(self):
                pass

        steps = TestPipeline._steps
        assert len(steps) == 1
        assert steps[0] == ("step_a", 1)


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
            async def step_b(self, call_next):
                return await call_next

            @step(order=1)
            async def step_a(self, call_next):
                return await call_next

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
    async def test_run_executes_all_steps_in_order(self):
        """Тест выполнения всех шагов по порядку."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                execution_order.append("step_a")
                return await call_next

            @step(order=2)
            async def step_b(self, call_next):
                execution_order.append("step_b")
                return await call_next

            @step(order=3)
            async def step_c(self, call_next):
                execution_order.append("step_c")
                return await call_next

        result = await TestPipeline.run()
        assert execution_order == ["step_a", "step_b", "step_c"]
        assert result.result is None  # Ни один шаг не вернул результат

    @pytest.mark.asyncio
    async def test_run_early_exit_on_result(self):
        """Тест раннего выхода при возврате результата."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                execution_order.append("step_a")
                return {"from": "step_a"}

            @step(order=2)
            async def step_b(self, call_next):
                execution_order.append("step_b")
                return await call_next

        result = await TestPipeline.run()
        assert execution_order == ["step_a"]
        assert result.result == {"from": "step_a"}

    @pytest.mark.asyncio
    async def test_run_early_exit_on_middle_step(self):
        """Тест раннего выхода на среднем шаге."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                execution_order.append("step_a")
                return await call_next

            @step(order=2)
            async def step_b(self, call_next):
                execution_order.append("step_b")
                return {"from": "step_b"}

            @step(order=3)
            async def step_c(self, call_next):
                execution_order.append("step_c")
                return await call_next

        result = await TestPipeline.run()
        assert execution_order == ["step_a", "step_b"]
        assert result.result == {"from": "step_b"}

    @pytest.mark.asyncio
    async def test_run_first_result_wins(self):
        """Тест, что учитывается только первый результат."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                execution_order.append("step_a")
                return {"from": "step_a"}

            @step(order=2)
            async def step_b(self, call_next):
                execution_order.append("step_b")
                return {"from": "step_b"}

        result = await TestPipeline.run()
        assert execution_order == ["step_a"]
        assert result.result == {"from": "step_a"}

    @pytest.mark.asyncio
    async def test_run_with_custom_context(self):
        """Тест запуска с кастомным контекстом."""

        class CustomCTX(PipeCTX):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.user_id = kwargs.get("user_id")

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                return {"user_id": self.ctx.user_id}

        result = await TestPipeline.run(ctx_factory=CustomCTX, user_id=42)
        assert result.result == {"user_id": 42}

    @pytest.mark.asyncio
    async def test_run_step_num_and_name_set(self):
        """Тест, что step_num и step_name устанавливаются корректно."""
        step_info = {}

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                step_info["step_a"] = (self.step_num, self.step_name)
                return await call_next

            @step(order=2)
            async def step_b(self, call_next):
                step_info["step_b"] = (self.step_num, self.step_name)
                return await call_next

        await TestPipeline.run()
        assert step_info["step_a"] == (1, "step_a")
        assert step_info["step_b"] == (2, "step_b")

    @pytest.mark.asyncio
    async def test_run_empty_pipeline_raises_error(self):
        """Тест, что запуск пайплайна без шагов вызывает ошибку."""

        class EmptyPipeline(Pipeline):
            pass

        with pytest.raises(RuntimeError, match="No steps assigned"):
            await EmptyPipeline.run()

    @pytest.mark.asyncio
    async def test_run_step_raises_exception(self):
        """Тест, что исключение в шаге пробрасывается."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await TestPipeline.run()

    @pytest.mark.asyncio
    async def test_run_step_after_exception_not_executed(self):
        """Тест, что шаги после исключения не выполняются."""
        execution_order = []

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                execution_order.append("step_a")
                raise RuntimeError("fail")

            @step(order=2)
            async def step_b(self, call_next):
                execution_order.append("step_b")
                return await call_next

        with pytest.raises(RuntimeError):
            await TestPipeline.run()
        assert execution_order == ["step_a"]

    @pytest.mark.asyncio
    async def test_run_returns_self(self):
        """Тест, что run возвращает экземпляр пайплайна."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                return await call_next

        result = await TestPipeline.run()
        assert isinstance(result, TestPipeline)

    @pytest.mark.asyncio
    async def test_step_can_access_ctx(self):
        """Тест доступа к контексту из шага."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                return {"ctx_id": self.ctx.id}

        result = await TestPipeline.run()
        assert "ctx_id" in result.result
        assert isinstance(result.result["ctx_id"], str)

    @pytest.mark.asyncio
    async def test_multiple_runs_produce_different_contexts(self):
        """Тест, что разные запуски имеют разные контексты."""

        class TestPipeline(Pipeline):
            @step(order=1)
            async def step_a(self, call_next):
                return {"ctx_id": self.ctx.id}

        result1 = await TestPipeline.run()
        result2 = await TestPipeline.run()
        assert result1.result["ctx_id"] != result2.result["ctx_id"]