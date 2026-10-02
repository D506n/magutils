"""HTTP-хуки выполняются внутри функции базового Runner."""

import httpx
import orjson
import pytest

from src.magutils.http.helpers import QHookRunner
from src.magutils.http.request import FluentReq


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_hook_supports_if_without_user_function(enabled):
    params, headers, body = await QHookRunner.run(
        'if body.pop("enabled"):\n'
        '    params["mode"] = "json"\n'
        '    headers["X-Mode"] = "json"\n'
        '    body["format"] = "json"\n'
        'else:\n'
        '    body["format"] = "text"',
        {}, {}, {"enabled": enabled},
    )
    assert params == ({"mode": "json"} if enabled else {})
    assert headers == ({"X-Mode": "json"} if enabled else {})
    assert body == {"format": "json" if enabled else "text"}


@pytest.mark.asyncio
async def test_hook_returns_reassigned_values_and_supports_for():
    params, headers, body = await QHookRunner.run(
        'params = {"page": "2"}\n'
        'headers = {"X-Mode": "replaced"}\n'
        'items = []\n'
        'for value in body["items"]:\n'
        '    if value > 1:\n'
        '        items.append(value)\n'
        'body = {"items": items}',
        {"old": "value"}, {"Old": "value"}, {"items": [1, 2, 3]},
    )
    assert params == {"page": "2"}
    assert headers == {"X-Mode": "replaced"}
    assert body == {"items": [2, 3]}


@pytest.mark.asyncio
async def test_fluent_request_executes_conditional_before_and_after():
    def respond(request):
        assert request.url.params["version"] == "2"
        assert request.headers["X-Mode"] == "json"
        assert orjson.loads(request.content) == {"format": "json"}
        return httpx.Response(
            200, json={"data": {"answer": "ok"}}, headers={"X-Provider": "test"},
        )

    request = FluentReq().method("POST").url("/generate").body({"enabled": True})
    request.script(
        'if body.pop("enabled"):\n'
        '    params["version"] = "2"\n'
        '    headers["X-Mode"] = "json"\n'
        '    body = {"format": "json"}',
        "before",
    )
    request.script(
        'if "data" in body:\n'
        '    body = body["data"]\n'
        '    headers["X-Processed"] = "yes"',
        "after",
    )
    request.script(
        'if headers["X-Processed"] == "yes":\n'
        '    body["second_hook"] = True',
        "after",
    )
    async with httpx.AsyncClient(
        base_url="https://llm.example", transport=httpx.MockTransport(respond),
    ) as client:
        response = await request.execute(client)
    assert response.json() == {"answer": "ok", "second_hook": True}
    assert response.headers["x-provider"] == "test"
    assert response.headers["X-Processed"] == "yes"
