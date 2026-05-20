import asyncio
import sys
from unittest.mock import patch, MagicMock
import pytest
from src.magutils.bg_tasks import BgTask

delay = 0.01


@pytest.fixture
def reset_bg_task():
    """Фикстура для сброса синглтона BgTask между тестами."""
    BgTask._BgTask__inst = None
    yield
    BgTask._BgTask__inst = None


class TestBgTask:
    
    @pytest.mark.asyncio
    async def test_create_single_task(self, reset_bg_task):
        """Тест создания одной задачи."""
        async def sample_coro():
            return "result"
        
        BgTask.create(sample_coro())
        
        # Проверяем, что задача добавлена
        assert len(BgTask._BgTask__inst.tasks) == 1
        
        # Ждем завершения задачи
        await asyncio.sleep(delay)
        
        # Проверяем, что задача удалена после завершения
        assert len(BgTask._BgTask__inst.tasks) == 0
    
    @pytest.mark.asyncio
    async def test_create_multiple_tasks(self, reset_bg_task):
        """Тест создания нескольких задач."""
        async def sample_coro(value):
            return value
        
        BgTask.create(
            sample_coro("task1"),
            sample_coro("task2"),
            sample_coro("task3")
        )
        
        # Проверяем, что все задачи добавлены
        assert len(BgTask._BgTask__inst.tasks) == 3
        
        # Ждем завершения задач
        await asyncio.sleep(delay)
        
        # Проверяем, что все задачи удалены после завершения
        assert len(BgTask._BgTask__inst.tasks) == 0
    
    @pytest.mark.asyncio
    async def test_task_exception_handling(self, reset_bg_task, caplog):
        """Тест обработки исключений в задачах."""
        async def failing_coro():
            raise ValueError("Test error")
        
        BgTask.create(failing_coro())
        
        # Ждем завершения задачи
        await asyncio.sleep(delay)
        
        # Проверяем, что сообщение об ошибке записано в лог
        assert "Got exception in background task. ValueError: Test error" in caplog.text
    
    @pytest.mark.asyncio
    async def test_task_critical_error_handling(self, reset_bg_task):
        """Тест обработки критических ошибок в задачах."""
        async def failing_coro():
            raise ValueError("Critical error")
        
        # Мокаем sys.exit для предотвращения завершения процесса
        with patch.object(sys, 'exit') as mock_exit:
            BgTask.create(failing_coro(), raise_errors=True)
            
            # Ждем завершения задачи
            await asyncio.sleep(0.1)
            
            # Проверяем, что sys.exit был вызван
            mock_exit.assert_called_once_with(1)
    
    def test_create_with_non_coroutine(self, reset_bg_task):
        """Тест создания задачи с не-корутиной."""
        with pytest.raises(TypeError, match="coro must be a coroutine"):
            BgTask.create("not a coroutine")
    
    @pytest.mark.asyncio
    async def test_task_done_callback(self, reset_bg_task):
        """Тест колбэка завершения задачи."""
        async def sample_coro():
            return "result"
        
        # Мокаем метод _task_done для проверки вызова
        with patch.object(BgTask, '_task_done') as mock_task_done:
            BgTask.create(sample_coro())
            
            # Ждем завершения задачи
            await asyncio.sleep(delay)
            
            # Проверяем, что колбэк был вызван
            mock_task_done.assert_called()