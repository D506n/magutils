import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.magutils.fsm.state import State
from src.magutils.fsm.types import StateError
from src.magutils.bg_tasks import BgTask


@pytest.fixture
def reset_bg_task():
    """Фикстура для сброса синглтона BgTask между тестами."""
    BgTask._BgTask__inst = None
    yield
    BgTask._BgTask__inst = None


class TestState:
    """Тесты для класса State."""

    @pytest.mark.asyncio
    async def test_state_creation(self, reset_bg_task):
        """Проверка создания состояния с корректными параметрами."""
        state = State("test", start=False, final=False)
        assert state.name == "test"
        assert state.start is False
        assert state.final is False
        assert state.enter_callback is None
        assert state.exit_callback is None
        assert state.progress_callback is None

    @pytest.mark.asyncio
    async def test_state_start_and_final(self, reset_bg_task):
        """Проверка флагов start и final."""
        start_state = State("start", start=True, final=False)
        assert start_state.start is True
        assert start_state.final is False

        final_state = State("final", start=False, final=True)
        assert final_state.start is False
        assert final_state.final is True

    @pytest.mark.asyncio
    async def test_state_cannot_be_both_start_and_final(self, reset_bg_task):
        """Проверка, что состояние не может быть одновременно start и final."""
        with pytest.raises(StateError, match="State cannot be both start and final"):
            State("invalid", start=True, final=True)

    @pytest.mark.asyncio
    async def test_on_enter_callback(self, reset_bg_task):
        """Проверка регистрации коллбэка on_enter."""
        state = State("test")
        callback = AsyncMock()
        decorated = state.on_enter(callback)
        assert decorated is callback
        assert state.enter_callback is callback

    @pytest.mark.asyncio
    async def test_on_exit_callback(self, reset_bg_task):
        """Проверка регистрации коллбэка on_exit."""
        state = State("test")
        callback = AsyncMock()
        decorated = state.on_exit(callback)
        assert decorated is callback
        assert state.exit_callback is callback

    @pytest.mark.asyncio
    async def test_on_exit_callback_final_state_raises(self, reset_bg_task):
        """Проверка, что final состояние не может иметь exit коллбэк."""
        state = State("final", final=True)
        callback = AsyncMock()
        with pytest.raises(StateError, match="Final state can call only enter callbacks!"):
            state.on_exit(callback)

    @pytest.mark.asyncio
    async def test_on_progress_callback(self, reset_bg_task):
        """Проверка регистрации коллбэка on_progress."""
        state = State("test")
        callback = AsyncMock()
        decorated = state.on_progress(callback)
        assert decorated is callback
        assert state.progress_callback is callback

    @pytest.mark.asyncio
    async def test_on_progress_callback_final_state_raises(self, reset_bg_task):
        """Проверка, что final состояние не может иметь progress коллбэк."""
        state = State("final", final=True)
        callback = AsyncMock()
        with pytest.raises(StateError, match="Final state can call only enter callbacks!"):
            state.on_progress(callback)

    @pytest.mark.asyncio
    async def test_emit_callback_enter(self, reset_bg_task):
        """Проверка вызова коллбэка при входе в состояние."""
        state = State("test")
        mock_callback = AsyncMock()
        state.on_enter(mock_callback)
        model = MagicMock()
        await state._emit_callback('EnterState', model)
        mock_callback.assert_called_once()
        event = mock_callback.call_args[0][0]
        assert event.type == 'EnterState'
        assert event.state is state
        assert event.model is model

    @pytest.mark.asyncio
    async def test_emit_callback_exit(self, reset_bg_task):
        """Проверка вызова коллбэка при выходе из состояния."""
        state = State("test")
        mock_callback = AsyncMock()
        state.on_exit(mock_callback)
        model = MagicMock()
        await state._emit_callback('ExitState', model)
        mock_callback.assert_called_once()
        event = mock_callback.call_args[0][0]
        assert event.type == 'ExitState'
        assert event.state is state
        assert event.model is model

    @pytest.mark.asyncio
    async def test_emit_callback_progress(self, reset_bg_task):
        """Проверка вызова коллбэка при прогрессе в состоянии."""
        state = State("test")
        mock_callback = AsyncMock()
        state.on_progress(mock_callback)
        model = MagicMock()
        await state._emit_callback('ProgressState', model)
        mock_callback.assert_called_once()
        event = mock_callback.call_args[0][0]
        assert event.type == 'ProgressState'
        assert event.state is state
        assert event.model is model

    @pytest.mark.asyncio
    async def test_emit_callback_no_callback(self, reset_bg_task):
        """Проверка, что если коллбэк не установлен, ничего не ломается."""
        state = State("test")
        model = MagicMock()
        # Не должно вызывать исключений
        await state._emit_callback('EnterState', model)
        await state._emit_callback('ExitState', model)
        await state._emit_callback('ProgressState', model)

    @pytest.mark.asyncio
    async def test_emit_callback_unknown_type(self, reset_bg_task):
        """Проверка ошибки при неизвестном типе коллбэка."""
        state = State("test")
        with pytest.raises(StateError, match="Unknown callback type"):
            await state._emit_callback('UnknownType', None)

    @pytest.mark.asyncio
    async def test_hash(self, reset_bg_task):
        """Проверка хэширования состояния по имени."""
        state1 = State("state1")
        state2 = State("state2")
        state3 = State("state1")
        assert hash(state1) == hash(state3)
        assert hash(state1) != hash(state2)
        assert state1 in {state1, state3}
        assert state2 not in {state1, state3}

    @pytest.mark.asyncio
    async def test_emit_callback_nowait(self, reset_bg_task):
        """Проверка асинхронного вызова коллбэка без ожидания."""
        state = State("test")
        mock_callback = AsyncMock()
        state.on_enter(mock_callback)
        model = MagicMock()
        # Запускаем nowait
        state._emit_callback_nowait('EnterState', model)
        # Даём время на выполнение задачи
        await asyncio.sleep(0.01)
        # Проверяем, что коллбэк был вызван
        mock_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_callback_exception_logged(self, reset_bg_task):
        """Проверка, что исключение в коллбэке логируется, но не прокидывается."""
        from src.magutils.fsm.state import logger
        state = State("test")
        
        async def failing_callback(event):
            raise ValueError("Test error")
        
        state.on_enter(failing_callback)
        model = MagicMock()
        
        with patch.object(logger, 'error') as mock_error:
            await state._emit_callback('EnterState', model)
            # Проверяем, что ошибка была залогирована
            mock_error.assert_called_once()
            # Убедимся, что исключение не прокинулось дальше
            # (тест не упал)