"""Cancellation must not return a context while its thread is still running."""

import asyncio
from contextvars import ContextVar
from threading import Event

import pytest

from magutils.star.starlark import BaseCTX, Runner, StarResult


class BlockingContext(BaseCTX):
    def __init__(self):
        self.entered = Event()
        self.release = Event()
        self.finished = Event()
        super().__init__()
        self.mod.add_callable('block', self.block)

    def block(self):
        self.entered.set()
        self.release.wait(2)
        self.finished.set()


async def wait_until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0.001)


@pytest.mark.asyncio
async def test_cancel_keeps_context_reserved_until_thread_finishes():
    runner = Runner(size=1, ctx_factory=BlockingContext)
    ctx = runner.ctxs.get_nowait()
    runner.ctxs.put_nowait(ctx)
    pending = asyncio.create_task(runner._run(
        'block()\nreturn input', {'old': True}, add_ctx={'private': 'test-secret'},
    ))
    following = None
    try:
        await wait_until(ctx.entered.is_set)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert not ctx.finished.is_set()
        assert runner.ctxs.qsize() == 0
        following = asyncio.create_task(runner._run('return input', {'new': True}))
        await asyncio.sleep(0)
        assert not following.done()
        ctx.release.set()
        result = await asyncio.wait_for(following, 2)
        assert result.result == {'new': True}
        assert ctx.finished.is_set()
        assert runner.ctxs.qsize() == 1
        assert ctx.mod['private'] is None
        assert ctx.mod['input'] == {}
    finally:
        ctx.release.set()
        pending.cancel()
        if following is not None:
            following.cancel()
        await asyncio.gather(pending, *([following] if following else []), return_exceptions=True)
        await wait_until(lambda: runner.ctxs.qsize() == 1)


@pytest.mark.asyncio
async def test_cancel_interrupts_interpreter_and_repeated_calls_do_not_lose_pool():
    runner = Runner(size=1)
    ctx = runner.ctxs.get_nowait()
    runner.ctxs.put_nowait(ctx)
    entered = Event()
    ctx.mod.add_callable('started', entered.set)
    for _ in range(6):
        entered.clear()
        pending = asyncio.create_task(runner._run(
            'started()\nfor i in range(100000000):\n    value = i * i\nreturn {"done": True}', {}
        ))
        try:
            await wait_until(entered.is_set)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            await wait_until(lambda: runner.ctxs.qsize() == 1)
        finally:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
    assert (await runner._run('return {"ok": True}', {})).result == {'ok': True}


@pytest.mark.asyncio
async def test_cancel_while_waiting_does_not_duplicate_or_lose_context():
    runner = Runner(size=1)
    async with runner.get_ctx():
        pending = asyncio.create_task(runner._run('return input', {}))
        await asyncio.sleep(0)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert runner.ctxs.qsize() == 0
    assert runner.ctxs.qsize() == 1


@pytest.mark.asyncio
async def test_get_ctx_returns_context_after_exception():
    runner = Runner(size=1)
    with pytest.raises(ValueError, match='test'):
        async with runner.get_ctx({'extra': 'value'}) as ctx:
            raise ValueError('test')
    assert runner.ctxs.qsize() == 1
    assert ctx.mod['extra'] is None


@pytest.mark.asyncio
async def test_invalid_script_and_input_release_context():
    runner = Runner(size=1)
    for script, data in [('if True', {}), ('return input', object())]:
        result = await runner._run(script, data)
        assert result.success is False
        assert runner.ctxs.qsize() == 1
    assert (await runner._run('return input', {'ok': True})).result == {'ok': True}


@pytest.mark.asyncio
async def test_executor_preserves_contextvars():
    marker = ContextVar('test_marker', default='outside')
    runner = Runner(size=1)
    ctx = runner.ctxs.get_nowait()
    ctx.mod.add_callable('get_marker', marker.get)
    runner.ctxs.put_nowait(ctx)
    token = marker.set('request')
    try:
        result = await runner._run('return {"value": get_marker()}', {})
    finally:
        marker.reset(token)
    assert result.result == {'value': 'request'}


def test_successful_none_result_and_unset_result_are_distinguished():
    result = StarResult()
    with pytest.raises(RuntimeError, match='not available'):
        _ = result.result
    result.result = None
    assert result.success and result.result is None
