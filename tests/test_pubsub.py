import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import pytest
from magutils.pubsub import PubSub


class TestEvent:
    """Тесты для класса Event."""

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self):
        """Тест подписки и отписки."""
        event = PubSub()
        mock_callback = AsyncMock()

        # Подписываемся
        unsubscribe = event.subscribe(mock_callback)
        assert len(event.subscribers) == 1

        # Отписываемся
        unsubscribe()
        assert len(event.subscribers) == 0

    @pytest.mark.asyncio
    async def test_subscribe_returns_callable(self):
        """Тест, что subscribe возвращает вызываемую функцию для отписки."""
        event = PubSub()
        mock_callback = AsyncMock()

        unsubscribe = event.subscribe(mock_callback)
        assert callable(unsubscribe)

        # Вызываем возвращенную функцию
        unsubscribe()
        assert len(event.subscribers) == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Тест нескольких подписчиков."""
        event = PubSub()
        mock1 = AsyncMock()
        mock2 = AsyncMock()
        mock3 = AsyncMock()

        event.subscribe(mock1)
        event.subscribe(mock2)
        event.subscribe(mock3)

        assert len(event.subscribers) == 3

    @pytest.mark.asyncio
    async def test_emit_calls_all_subscribers(self):
        """Тест, что emit вызывает всех подписчиков."""
        event = PubSub()
        mock1 = AsyncMock()
        mock2 = AsyncMock()

        event.subscribe(mock1)
        event.subscribe(mock2)

        payload = {"data": "test"}
        event.emit(payload)

        # Даем время на выполнение асинхронных задач
        await asyncio.sleep(0.01)

        # Проверяем, что колбэки были вызваны с правильным payload
        mock1.assert_called_once_with(payload)
        mock2.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_emit_with_no_subscribers(self):
        """Тест emit без подписчиков (не должно падать)."""
        event = PubSub()
        payload = {"data": "test"}

        # Не должно вызывать исключений
        event.emit(payload)
        await asyncio.sleep(0.01)  # Даем время на выполнение

    @pytest.mark.asyncio
    async def test_unsubscribe_with_invalid_key(self):
        """Тест отписки с несуществующим ключом (должно логировать предупреждение)."""
        event = PubSub()
        with patch('magutils.pubsub.logger') as mock_logger:
            event.unsubscribe("invalid_key")
            mock_logger.warning.assert_called_once_with('Key %s not found', 'invalid_key')

    @pytest.mark.asyncio
    async def test_emit_raise_errors_true(self):
        """Тест emit с raise_errors=True (ошибки должны вызывать sys.exit)."""
        event = PubSub()
        
        async def failing_callback(payload):
            raise ValueError("Critical error")

        event.subscribe(failing_callback)

        with patch('sys.exit') as mock_exit:
            with patch('magutils.bg_tasks.logger') as mock_logger:
                event.emit({"test": "data"}, raise_errors=True)
                await asyncio.sleep(0.01)
            
                # Проверяем, что sys.exit был вызван
                mock_exit.assert_called_once_with(1)
                mock_logger.critical.assert_called_once_with('Got critical error in background task. %s', ANY)

    def test_subscribe_with_sync_callback_raises(self):
        """Тест, что синхронный колбэк вызывает TypeError при вызове."""
        event = PubSub()
        
        def sync_callback(payload):
            pass
        
        # Подписка должна пройти (тип не проверяется при подписке)
        # Но при emit будет ошибка, так как колбэк не асинхронный
        # Это тестируется в test_emit_with_sync_callback
        unsubscribe = event.subscribe(sync_callback)
        assert callable(unsubscribe)

    @pytest.mark.asyncio
    async def test_emit_with_sync_callback(self):
        """Тест emit с синхронным колбэком (должен упасть при выполнении)."""
        event = PubSub()
        
        def sync_callback(payload):
            pass
        
        event.subscribe(sync_callback)
        
        with pytest.raises(TypeError, match='coro must be a Awaitable'):
            event.emit(None)


    @pytest.mark.asyncio
    async def test_event_with_generic_type(self):
        """Тест Event с generic типом."""
        event = PubSub[str]()  # Специализация для строки
        mock_callback = AsyncMock()
        
        event.subscribe(mock_callback)
        event.emit("test payload")
        
        await asyncio.sleep(0.01)
        mock_callback.assert_called_once_with("test payload")