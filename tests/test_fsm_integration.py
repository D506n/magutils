import asyncio
import pytest
from unittest.mock import AsyncMock
from pydantic import BaseModel
from src.magutils.fsm.state import State
from src.magutils.fsm.group import StateGroup

class UserModel(BaseModel):
    name: str
    score: int = 0

class OrderModel(BaseModel):
    order_id: str
    amount: float
    status: str = "created"


class TestFSMIntegration:
    """Интеграционные тесты для всего модуля FSM."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_callbacks(self):
        """Полный рабочий процесс с коллбэками на каждом этапе."""
        class OrderFSM(StateGroup[OrderModel]):
            created = State("created", start=True)
            paid = State("paid")
            shipped = State("shipped")
            delivered = State("delivered", final=True)

        # Регистрируем коллбэки
        start_calls = []
        finish_calls = []
        enter_calls = []
        exit_calls = []

        @OrderFSM.on_start
        async def on_start(event):
            start_calls.append(event)

        @OrderFSM.on_finish
        async def on_finish(event):
            finish_calls.append(event)

        @OrderFSM.created.on_exit
        async def on_exit_created(event):
            exit_calls.append(("created", event))

        @OrderFSM.paid.on_enter
        async def on_enter_paid(event):
            enter_calls.append(("paid", event))

        @OrderFSM.paid.on_exit
        async def on_exit_paid(event):
            exit_calls.append(("paid", event))

        @OrderFSM.shipped.on_enter
        async def on_enter_shipped(event):
            enter_calls.append(("shipped", event))

        @OrderFSM.delivered.on_enter
        async def on_enter_delivered(event):
            enter_calls.append(("delivered", event))

        # Создаём FSM с моделью
        model = OrderModel(order_id="123", amount=99.99)
        fsm = OrderFSM(model=model)

        # Даём время на вызов стартового коллбэка
        await asyncio.sleep(0.01)
        assert len(start_calls) == 1
        assert start_calls[0].group is fsm
        assert start_calls[0].model is model

        # Переходы
        await fsm.emit("paid")
        assert fsm.current_state.name == "paid"
        assert len(exit_calls) == 1
        assert exit_calls[0][0] == "created"
        assert len(enter_calls) == 1
        assert enter_calls[0][0] == "paid"

        await fsm.emit("shipped")
        assert fsm.current_state.name == "shipped"
        assert len(exit_calls) == 2
        assert exit_calls[1][0] == "paid"
        assert len(enter_calls) == 2
        assert enter_calls[1][0] == "shipped"

        await fsm.emit("delivered")
        assert fsm.current_state.name == "delivered"
        assert len(enter_calls) == 3
        assert enter_calls[2][0] == "delivered"
        assert len(finish_calls) == 1
        assert finish_calls[0].group is fsm

        # Проверяем, что из финального состояния нельзя выйти
        with pytest.raises(Exception, match="Current state is final"):
            await fsm.emit("paid")

    @pytest.mark.asyncio
    async def test_dump_and_load_preserves_state(self):
        """Проверка сериализации и десериализации с сохранением состояния."""
        class SimpleFSM(StateGroup):
            a = State("a", start=True)
            b = State("b")
            c = State("c", final=True)

        fsm = SimpleFSM(id="original")
        await fsm.emit("b")
        assert fsm.current_state.name == "b"

        # Дамп
        packed = await fsm.dump()
        assert packed["id"] == "original"
        assert packed["current_state"] == "b"
        assert packed["model"]["path"] is None

        # Загрузка
        loaded = SimpleFSM.load(packed)
        assert loaded.id == "original"
        assert loaded.current_state.name == "b"
        assert loaded.model is None
        # Проверяем, что можно продолжить работу
        await loaded.emit("c")
        assert loaded.current_state.name == "c"

    @pytest.mark.asyncio
    async def test_concurrent_emits_are_serialized(self):
        """Проверка, что параллельные вызовы emit выполняются последовательно."""
        class ConcurrentFSM(StateGroup):
            s1 = State("s1", start=True)
            s2 = State("s2")
            s3 = State("s3")

        fsm = ConcurrentFSM()
        execution_order = []

        @fsm.all_states["s1"].on_exit
        async def exit_s1(event):
            execution_order.append("exit_s1")
            await asyncio.sleep(0.05)  # Искусственная задержка

        @fsm.all_states["s2"].on_enter
        async def enter_s2(event):
            execution_order.append("enter_s2")

        @fsm.all_states["s2"].on_exit
        async def exit_s2(event):
            execution_order.append("exit_s2")

        @fsm.all_states["s3"].on_enter
        async def enter_s3(event):
            execution_order.append("enter_s3")

        # Запускаем два перехода "одновременно"
        task1 = asyncio.create_task(fsm.emit("s2"))
        task2 = asyncio.create_task(fsm.emit("s3"))
        await asyncio.gather(task1, task2)

        # Проверяем порядок: exit_s1 -> enter_s2 -> exit_s2 -> enter_s3
        assert execution_order == ["exit_s1", "enter_s2", "exit_s2", "enter_s3"]
        assert fsm.current_state.name == "s3"

    @pytest.mark.asyncio
    async def test_model_persistence_through_transitions(self):
        """Проверка, что модель сохраняется через переходы и дамп/загрузку."""

        class GameFSM(StateGroup[UserModel]):
            menu = State("menu", start=True)
            playing = State("playing")
            game_over = State("game_over", final=True)

        user = UserModel(name="Alice", score=100)
        fsm = GameFSM(model=user)

        # Меняем модель внутри коллбэка
        @GameFSM.playing.on_enter
        async def add_score(event):
            event.model.score += 50

        await fsm.emit("playing")
        assert fsm.model.score == 150

        # Дамп
        packed = await fsm.dump()
        assert packed["model"]["data"]["score"] == 150

        # Загрузка
        loaded = GameFSM.load(packed)
        assert loaded.model.name == "Alice"
        assert loaded.model.score == 150
        assert loaded.current_state.name == "playing"