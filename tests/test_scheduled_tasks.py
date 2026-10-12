import asyncio as aio
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import cron_parser_py as cron
import pytest

from magutils.scheduled_tasks import (
    CronTask,
    OneTimeTask,
    ScheduledTask,
    Scheduler,
)
from magutils.time_utils import get_current_time, get_tz, parse_time


class TestScheduledTask:
    @pytest.mark.asyncio
    async def test_emit(self):
        with patch.object(ScheduledTask, 'parse_expr'):
            task = ScheduledTask('', 123)
            receiver = AsyncMock()
            key = task.subscribe(receiver)
            assert isinstance(key, str)
            await task.emit()
            receiver.assert_called_once_with(123)
            await task.emit(1)
            receiver.assert_called_with(1)
            task.unsubscribe(key)
            await task.emit()
            assert receiver.call_count == 2

    @pytest.mark.asyncio
    async def test_emit_done_state(self):
        with patch.object(ScheduledTask, 'parse_expr'):
            task = ScheduledTask('', 123)
            await task.emit()
            assert task.fsm.current_state.name == 'done'

    @pytest.mark.asyncio
    async def test_emit_error_state(self):
        with patch.object(ScheduledTask, 'parse_expr'):
            task = ScheduledTask('', 123)

            async def bad(payload):
                raise RuntimeError('boom')

            task.subscribe(bad)
            await task.emit()
            assert task.fsm.current_state.name == 'error'

    @pytest.mark.asyncio
    async def test_dump(self):
        with patch.object(ScheduledTask, 'parse_expr'):
            task = ScheduledTask('', 123, id='test-id')
            assert task.dump() == {
                'raw_expr': '',
                'executions': 0,
                'payload': 123,
                'id': 'test-id',
                'state': 'created',
            }

    @pytest.mark.asyncio
    async def test_state_restore(self):
        with patch.object(ScheduledTask, 'parse_expr'):
            task = ScheduledTask('', 123, id='test-id', state='done')
            assert task.fsm.current_state.name == 'done'


class TestCronTask:
    @pytest.mark.asyncio
    async def test_parse_expr(self):
        expr = '* * * * *'
        task = CronTask(expr, 123)
        assert task.expr == cron.parse(expr)

    @pytest.mark.asyncio
    async def test_next_run(self):
        expect = get_current_time()
        expect = expect.replace(
            month=1, day=1, hour=12, minute=0, second=0, microsecond=0
        )
        if get_current_time() > expect:
            expect = expect.replace(year=expect.year + 1)
        expr = '0 12 1 1 *'
        task = CronTask(expr, 123)
        assert task.next_run == expect

    def test_match(self):
        expr = '0 12 1 1 *'
        assert CronTask.match(expr)
        expr = 'alalala'
        assert not CronTask.match(expr)


class TestOneTimeTask:
    @pytest.mark.asyncio
    async def test_parse_expr(self):
        expr = '2121-01-01 12:00'
        expect = parse_time(expr, '%Y-%m-%d %H:%M').replace(tzinfo=get_tz())
        task = OneTimeTask(expr, 123)
        assert task.next_run == expect

    def test_match(self):
        expr = '2121-01-01 12:00'
        assert OneTimeTask.match(expr)
        assert not OneTimeTask.match('alalala')


class TestScheduler:
    @pytest.mark.asyncio
    async def test_add_task(self):
        ot_expr = '2121-01-01 12:00'
        cron_expr = '0 12 1 1 *'
        err_expr = 'alalalala'
        with patch.object(Scheduler, 'main') as main:
            sch = Scheduler()
            sch.add_task(ot_expr, 123)
            await aio.sleep(0.1)
            main.assert_called_once()
            sch.add_task(cron_expr, 123)
            main.assert_called_once()
            with pytest.raises(ValueError, match='Invalid expression'):
                sch.add_task(err_expr, 123)
            main.assert_called_once()
            assert len(sch.tasks) == 2

    @pytest.mark.asyncio
    async def test_load_task(self):
        with patch.object(Scheduler, 'main'):
            sch = Scheduler()
            dumped = {
                'raw_expr': '2121-01-01 12:00',
                'executions': 0,
                'payload': 123,
                'id': 'test-id',
                'state': 'created',
            }
            task = sch.load_task(dumped)
            assert task.id == 'test-id'
            assert task.payload == 123
            assert task.fsm.current_state.name == 'created'
            assert sch.tasks['test-id'] is task
            with pytest.raises(ValueError, match='Invalid expression'):
                sch.load_task({**dumped, 'raw_expr': 'alalala'})

    @pytest.mark.asyncio
    async def test_exec_wrapper(self, caplog):
        def gct():
            dt = get_current_time()
            return dt + timedelta(seconds=1)
        mock = AsyncMock()
        dt = get_current_time()
        past_task = OneTimeTask[int]('1970-01-01 00:00', 123)
        task = OneTimeTask(dt.strftime('%Y-%m-%d %H:%M'), 123)
        cron_task = CronTask('* * * * *', 123)
        gct.cache_clear = Mock()
        cron_task.calc_next_run = gct  # чтобы не ждать
        with patch.object(Scheduler, 'main'):
            sch = Scheduler()
            caplog.set_level(logging.WARNING)
            await sch.exec_wrapper(past_task)
            assert 'Task execution time was missed.: ' in caplog.text
            task.subscribe(mock)
            caplog.set_level(logging.INFO)
            await sch.exec_wrapper(task)
            assert 'New task: ' in caplog.text
            await aio.sleep(0.1)
            mock.assert_called_once_with(123)
            await sch.exec_wrapper(cron_task)
            assert 'rescheduled' in caplog.text

    @pytest.mark.asyncio
    async def test_main(self):
        sc = Scheduler()
        dt = get_current_time()
        sc.add_task(dt.strftime('%Y-%m-%d %H:%M'), 123)
        await aio.sleep(0.1)
        sc.shutdown()
        assert sc.alive is False
        await aio.sleep(0.1)
        assert sc.main_task.done()