"""Invalid HTTP hook results have a stable error type without their contents."""

import httpx
import pytest
from starlark import StarlarkError

from magutils.http import FluentReq, HookResultError
from magutils.http.helpers import QHookRunner


@pytest.mark.asyncio
@pytest.mark.parametrize('script', [
    'return',
    'return None',
    'return {"credential": "test-secret"}',
    'return params, headers',
    'return params, headers, body, "test-secret"',
    'params = "test-secret"',
    'headers = []',
    'body = {1: "test-secret"}',
])
async def test_invalid_result_raises_hook_result_error_without_data(script):
    with pytest.raises(HookResultError) as error:
        await QHookRunner.run(script, {}, {}, {})
    assert 'test-secret' not in str(error.value)
    assert (await QHookRunner.run('body["ok"] = True', {}, {}, {}))[2] == {'ok': True}


@pytest.mark.asyncio
@pytest.mark.parametrize('body', ['{}', '[]', '"text"', '42', 'True', 'None', 'struct(value=1)'])
async def test_all_json_body_types_are_supported(body):
    result = await QHookRunner.run(f'body = {body}', {}, {}, {})
    assert len(result) == 3


@pytest.mark.asyncio
async def test_script_error_remains_starlark_error():
    with pytest.raises(StarlarkError):
        await QHookRunner.run('fail("script error")', {}, {}, {})


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['before', 'after'])
async def test_fluent_request_propagates_result_error(stage):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={})

    request = FluentReq().method('POST').url('/test').script('return', stage)
    async with httpx.AsyncClient(
        base_url='https://example.test', transport=httpx.MockTransport(respond),
    ) as client:
        with pytest.raises(HookResultError):
            await request.execute(client)
    assert len(calls) == (1 if stage == 'after' else 0)
