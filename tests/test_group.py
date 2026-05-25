import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel
from src.magutils.fsm.state import State
from src.magutils.fsm.group import StateGroup
from src.magutils.fsm.types import StateError
from src.magutils.bg_tasks import BgTask


@pytest.fixture
def reset_bg_task():
    """Фикстура для сброса синглтона BgTask между тестами."""
    BgTask._BgTask__inst = None
    yield
    BgTask._BgTask__inst = None


class SimpleModel(BaseModel):
    value: int = 42


class TestStateGroup:
    """Тесты для класса StateGroup."""

    @pytest.mark.asyncio
    async def test_group_creation_with_defaults(self, reset_bg_task):
        """Проверка создания группы состояний с дефолтными параметрами."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)
            state2 = State("state2")

        group = MyGroup()
        assert group.id is not None
        assert group.current_state.name == "state1"
        assert group.model is None
        assert group.all_states["state1"] is MyGroup.state1
        assert group.all_states["state2"] is MyGroup.state2

    @pytest.mark.asyncio
    async def test_group_creation_with_custom_id_and_state(self, reset_bg_task):
        """Проверка создания группы с указанными id и текущим состоянием."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)
            state2 = State("state2")

        group = MyGroup(id="custom-id", current_state="state2")
        assert group.id == "custom-id"
        assert group.current_state.name == "state2"

    @pytest.mark.asyncio
    async def test_group_creation_with_model(self, reset_bg_task):
        """Проверка создания группы с моделью."""
        class MyGroup(StateGroup[SimpleModel]):
            state1 = State("state1", start=True)

        model = SimpleModel(value=100)
        group = MyGroup(model=model)
        assert group.model is model

    @pytest.mark.asyncio
    async def test_group_creation_unknown_state_raises(self, reset_bg_task):
        """Проверка ошибки при указании неизвестного состояния."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        with pytest.raises(StateError, match="Unknown state"):
            MyGroup(current_state="unknown")

    @pytest.mark.asyncio
    async def test_group_validation_multiple_start_states(self, reset_bg_task):
        """Проверка ошибки при нескольких стартовых состояниях."""
        with pytest.raises(StateError, match="Only one state can be start"):
            class InvalidGroup(StateGroup):
                s1 = State("s1", start=True)
                s2 = State("s2", start=True)

            error = InvalidGroup()

    @pytest.mark.asyncio
    async def test_group_validation_no_start_state(self, reset_bg_task):
        """Проверка ошибки при отсутствии стартового состояния."""
        with pytest.raises(StateError, match="No start state provided"):
            class InvalidGroup(StateGroup):
                s1 = State("s1")

            error = InvalidGroup()

    @pytest.mark.asyncio
    async def test_group_validation_duplicate_state_names(self, reset_bg_task):
        """Проверка ошибки при дублировании имён состояний."""
        with pytest.raises(StateError, match="State names must be unique"):
            class InvalidGroup(StateGroup):
                s1 = State("same", start=True)
                s2 = State("same")

            error = InvalidGroup()

    @pytest.mark.asyncio
    async def test_emit_transition(self, reset_bg_task):
        """Проверка перехода между состояниями."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)
            state2 = State("state2")

        group = MyGroup()
        enter_mock = AsyncMock()
        exit_mock = AsyncMock()
        MyGroup.state1.on_exit(exit_mock)
        MyGroup.state2.on_enter(enter_mock)

        await group.emit("state2")
        exit_mock.assert_called_once()
        enter_mock.assert_called_once()
        assert group.current_state.name == "state2"

    @pytest.mark.asyncio
    async def test_emit_same_state_calls_progress(self, reset_bg_task):
        """Проверка, что вызов emit с тем же состоянием вызывает progress."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        group = MyGroup()
        progress_mock = AsyncMock()
        MyGroup.state1.on_progress(progress_mock)

        await group.emit("state1")
        progress_mock.assert_called_once()
        assert group.current_state.name == "state1"

    @pytest.mark.asyncio
    async def test_emit_to_final_state_triggers_finish(self, reset_bg_task):
        """Проверка, что переход в финальное состояние вызывает finish коллбэк."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)
            state2 = State("state2", final=True)

        finish_mock = AsyncMock()
        MyGroup.on_finish(finish_mock)
        group = MyGroup()

        await group.emit("state2")
        finish_mock.assert_called_once()
        assert group.current_state.name == "state2"

    @pytest.mark.asyncio
    async def test_emit_from_final_state_raises(self, reset_bg_task):
        """Проверка, что из финального состояния нельзя перейти."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)
            state2 = State("state2", final=True)

        group = MyGroup()
        await group.emit("state2")
        with pytest.raises(StateError, match="Current state is final"):
            await group.emit("state1")

    @pytest.mark.asyncio
    async def test_emit_invalid_state_raises(self, reset_bg_task):
        """Проверка ошибки при переходе в несуществующее состояние."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        group = MyGroup()
        with pytest.raises(StateError, match="Invalid state"):
            await group.emit("invalid")

    @pytest.mark.asyncio
    async def test_emit_nowait(self, reset_bg_task):
        """Проверка асинхронного перехода без ожидания."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)
            state2 = State("state2")

        group = MyGroup()
        enter_mock = AsyncMock()
        MyGroup.state2.on_enter(enter_mock)

        group.emit_nowait("state2")
        # Даём время на выполнение
        await asyncio.sleep(0.01)
        enter_mock.assert_called_once()
        assert group.current_state.name == "state2"

    @pytest.mark.asyncio
    async def test_dump_without_model(self, reset_bg_task):
        """Проверка дампа группы без модели."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        group = MyGroup(id="test-id")
        await group.emit("state1")  # Чтобы can_pack был установлен
        dumped = await group.dump()
        assert dumped["name"] == "MyGroup"
        assert dumped["id"] == "test-id"
        assert dumped["current_state"] == "state1"
        assert dumped["model"]["path"] is None
        assert dumped["model"]["data"] is None

    @pytest.mark.asyncio
    async def test_dump_with_model(self, reset_bg_task):
        """Проверка дампа группы с моделью."""
        class MyGroup(StateGroup[SimpleModel]):
            state1 = State("state1", start=True)

        model = SimpleModel(value=99)
        group = MyGroup(id="test-id", model=model)
        await group.emit("state1")
        dumped = await group.dump()
        assert dumped["model"]["path"] == "tests.test_group.SimpleModel"
        assert dumped["model"]["data"] == {"value": 99}

    @pytest.mark.asyncio
    async def test_load_without_model(self, reset_bg_task):
        """Проверка загрузки группы без модели."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)
            state2 = State("state2")

        pack = {
            "name": "MyGroup",
            "id": "loaded-id",
            "current_state": "state2",
            "model": {"path": None, "data": None}
        }
        group = MyGroup.load(pack)
        assert group.id == "loaded-id"
        assert group.current_state.name == "state2"
        assert group.model is None
        # Проверяем, что коллбэки старта и входа не вызывались
        # (поскольку skip_init=True)

    @pytest.mark.asyncio
    async def test_load_with_model(self, reset_bg_task):
        """Проверка загрузки группы с моделью."""
        class MyGroup(StateGroup[SimpleModel]):
            state1 = State("state1", start=True)

        pack = {
            "name": "MyGroup",
            "id": "loaded-id",
            "current_state": "state1",
            "model": {
                "path": "tests.test_group.SimpleModel",
                "data": {"value": 777}
            }
        }
        group = MyGroup.load(pack)
        assert group.id == "loaded-id"
        assert group.current_state.name == "state1"
        assert isinstance(group.model, SimpleModel)
        assert group.model.value == 777

    @pytest.mark.asyncio
    async def test_load_with_invalid_name_raises(self, reset_bg_task):
        """Проверка ошибки при несоответствии имени группы."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        pack = {
            "name": "WrongGroup",
            "id": "id",
            "current_state": "state1",
            "model": {"path": None, "data": None}
        }
        with pytest.raises(StateError, match="Invalid state group name"):
            MyGroup.load(pack)

    @pytest.mark.asyncio
    async def test_load_with_model_strict_mode(self, reset_bg_task):
        """Проверка строгого режима загрузки модели."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        pack = {
            "name": "MyGroup",
            "id": "id",
            "current_state": "state1",
            "model": {
                "path": "nonexistent.module.Model",
                "data": {}
            }
        }
        # В строгом режиме должно вызывать исключение
        with pytest.raises(StateError, match="Failed to load model"):
            MyGroup.load(pack.copy(), strict=True)
        # В нестрогом режиме должно только залогировать warning
        with patch('src.magutils.fsm.group.logger') as mock_logger:
            group = MyGroup.load(pack.copy(), strict=False)
            assert group.model is None
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_on_start_decorator(self, reset_bg_task):
        """Проверка декоратора on_start."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        callback = AsyncMock()
        MyGroup.on_start(callback)
        assert MyGroup.start_callback is callback

    @pytest.mark.asyncio
    async def test_on_finish_decorator(self, reset_bg_task):
        """Проверка декоратора on_finish."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        callback = AsyncMock()
        MyGroup.on_finish(callback)
        assert MyGroup.finish_callback is callback

    @pytest.mark.asyncio
    async def test_start_callback_called_on_init(self, reset_bg_task):
        """Проверка, что коллбэк старта вызывается при инициализации."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        start_mock = AsyncMock()
        MyGroup.on_start(start_mock)
        group = MyGroup()
        # Даём время на выполнение асинхронного коллбэка
        await asyncio.sleep(0.01)
        start_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_init(self, reset_bg_task):
        """Проверка, что при skip_init коллбэки старта не вызываются."""
        class MyGroup(StateGroup):
            state1 = State("state1", start=True)

        start_mock = AsyncMock()
        MyGroup.on_start(start_mock)
        group = MyGroup(skip_init=True)
        await asyncio.sleep(0.01)
        start_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_model_caching(self, reset_bg_task):
        """Проверка кэширования моделей при загрузке."""
        from src.magutils.fsm.group import MODELS_CACHE
        # Очистим кэш перед тестом
        MODELS_CACHE.clear()

        class MyGroup(StateGroup[SimpleModel]):
            state1 = State("state1", start=True)

        pack = {
            "name": "MyGroup",
            "id": "id1",
            "current_state": "state1",
            "model": {
                "path": "tests.test_group.SimpleModel",
                "data": {"value": 42}
            }
        }
        # Первая загрузка
        group1 = MyGroup.load(pack)
        assert isinstance(group1.model, SimpleModel)
        assert group1.model.value == 42
        # Проверяем, что модель добавлена в кэш
        assert "tests.test_group.SimpleModel" in MODELS_CACHE
        cached_model = MODELS_CACHE["tests.test_group.SimpleModel"]
        assert cached_model is SimpleModel

        # Вторая загрузка с другим id, но той же моделью
        pack2 = pack.copy()
        pack2["id"] = "id2"
        # Замокаем importlib.import_module, чтобы убедиться, что он не вызывается
        with patch('importlib.import_module') as mock_import:
            group2 = MyGroup.load(pack2)
            # import_module не должен вызываться, так как модель в кэше
            mock_import.assert_not_called()
        assert group2.model.value == 42
        assert group2.id == "id2"