from magutils.scheduled_tasks import CronTask, OneTimeTask, Scheduler, ScheduledTask
import cron_parser_py as cron
from src.magutils.time_utils import get_current_time, parse_time, get_tz
import pytest
from unittest.mock import AsyncMock, patch, Mock
import asyncio as aio
import logging
from src.magutils.bg_tasks import BgTask


class TestScheduledTask:
    @pytest.mark.asyncio
    async def test_emit(self):
        with patch.object(ScheduledTask, 'parse_expr'):
            task = ScheduledTask('', 123)
            receiver = AsyncMock()
            key = task.subscribe(receiver)
            assert isinstance(key, str)
            task.emit()
            await aio.sleep(0.1)
            receiver.assert_called_once_with(123)
            task.emit(1)
            await aio.sleep(0.1)
            receiver.assert_called_with(1)
            task.unsubscribe(key)
            task.emit()
            await aio.sleep(0.1)
            assert receiver.call_count == 2


class TestCronTask:
    def test_parse_expr(self):
        expr = '* * * * *'
        task = CronTask(expr, 123)
        assert task.expr == cron.parse(expr)

    def test_next_run(self):
        expect = get_current_time()
        expect = expect.replace(month=1, day=1, hour=12, minute=0, second=0, microsecond=0)
        if get_current_time()>expect:
            expect = expect.replace(year=expect.year+1)
        expr = '0 12 1 1 *'
        task = CronTask(expr, 123)
        assert task.next_run == expect

    def test_match(self):
        expr = '0 12 1 1 *'
        assert CronTask.match(expr)
        expr = 'alalala'
        assert not CronTask.match(expr)


class TestOneTimeTask:
    def test_parse_expr(self):
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
    async def test_exec_wrapper(self, caplog):
        def gct():
            dt = get_current_time()
            return dt.replace(second=dt.second+1)
        mock = AsyncMock()
        dt = get_current_time()
        past_task = OneTimeTask[int]('1970-01-01 00:00', 123)
        task = OneTimeTask(dt.strftime('%Y-%m-%d %H:%M'), 123)
        cron_task = CronTask('* * * * *', 123)
        gct.cache_clear = Mock()
        cron_task.calc_next_run = gct # чтобы не ждать
        with patch.object(Scheduler, 'main') as main:
            sch = Scheduler()
            caplog.set_level(logging.WARNING)
            await sch.exec_wrapper(past_task)
            assert 'Task cannot be executed in past time' in caplog.text
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
        # mock.assert_called_once()
        sc.shutdown()
        assert sc.alive == False
        await aio.sleep(0.1)
        assert sc.main_task.done()