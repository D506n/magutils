from asyncio import Lock
from logging import getLogger
from typing import Literal, Self, TypedDict

import orjson
from httpx import AsyncClient, Response

from .helpers import QHookRunner

logger = getLogger(__name__)

METHODS_SET = set(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
METHODS = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class DumpResult(TypedDict):
    method: METHODS
    base_url: str
    url: str
    params: dict[str, str]
    headers: dict[str, str]
    cookies: dict[str, str]
    body: dict
    curl: str | None


class ROProxy:
    def __init__(self, obj):
        self.__obj = obj
        self.method: METHODS
        self.base_url: str
        self.url: str
        self.params: dict[str, str]
        self.headers: dict[str, str]
        self.cookies: dict[str, str]
        self.body: dict
        self.retries: int
        self.before_scripts: list[str]
        self.after_scripts: list[str]

    @property
    def sec_headers(self):
        result = self.headers.copy()
        unsecure_headers = ['Authorization', 'authorization']
        for head in unsecure_headers:
            if _ := result.pop(head, None):
                result[head] = '***'
        return result

    def __getattr__(self, name):
        return getattr(self.__obj, f'_{name}', None)

    def dump(self, with_curl=False) -> DumpResult:
        result = {
            "method": self.method,
            "base_url": self.base_url,
            "url": self.url,
            "params": self.params,
            "headers": self.sec_headers,
            "cookies": self.cookies,
            "body": self.body,
            "curl": None
        }
        if with_curl:
            result['curl'] = self.curl
        return result

    @property
    def curl(self):
        url = f'{self.base_url}{self.url}'
        if self.params:
            url += '?'
            url += "&".join([f"{k}={v}" for k, v in self.params.items()])
        curl_headers = ''
        if self.headers:
            curl_headers = ' --header '
            curl_headers += ' --header '.join(
                f"'{k}: {v}'" for k, v in self.sec_headers.items())
        curl_data = ''
        if self.body:
            curl_data += f" --data '{orjson.dumps(self.body).decode()}'"
        return (f"curl --request {self.method}"
                    f" --url '{url}'{curl_headers}{curl_data}")


class FluentReq:
    def __init__(self, base_url: str = None):
        self.__method: METHODS = None
        self._base_url: str = base_url
        self._url: str = ''
        self._params: dict[str, str] = {}
        self._headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self._cookies: dict[str, str] = {}
        self._body: dict = {}
        self._retries: int = 3
        self._before_scripts: list[str] = []
        self._after_scripts: list[str] = []
        self.__ro = ROProxy(self)
        self._before_scripts_done = False
        self._serialized_body: bytes = None
        self.__lock = Lock()

    @property
    def _method(self):
        if self.__method:
            return self.__method
        if self._body:
            return 'POST'
        else:
            return 'GET'

    def method(self, method: METHODS) -> Self:
        self.__method = method
        return self

    def base_url(self, url: str) -> Self:
        self._base_url = url
        return self

    def url(self, url: str) -> Self:
        self._url = url
        return self

    def params(self, params: dict[str, str]) -> Self:
        self._params.update(params)
        return self

    def headers(self, headers: dict[str, str]) -> Self:
        self._headers.update(headers)
        return self

    def cookies(self, cookies: dict[str, str]) -> Self:
        self._cookies.update(cookies)
        return self

    def body(self, data: dict) -> Self:
        self._serialized_body = None
        self._body.update(data)
        return self

    def retries(self, retries: int) -> Self:
        self._retries = retries
        return self

    def reload_scripts(self) -> Self:
        self._before_scripts_done = False
        return self

    def script(
        self, script: str, typ: Literal["before", "after"] = "before"
    ) -> Self:
        if typ == "before":
            self._before_scripts_done = False
            self._before_scripts.append(script)
        else:
            self._after_scripts.append(script)
        return self

    async def __exec_script(self, script: str):
        self._params, self._headers, self._body = await QHookRunner.run(
            script, self._params, self._headers, self._body)

    async def __exec_afterscripts(self, resp: Response):
        params = {}
        try:
            body = orjson.loads(resp.content)
        except orjson.JSONDecodeError:
            logger.error('Can\'t execute afterscripts, body is not valid json.')
            return resp
        for script in self._after_scripts:
            params, resp.headers, body = await QHookRunner.run(
                script, params, resp.headers, body
            )
        resp._content = orjson.dumps(body)
        return resp

    async def __execute(self, client: AsyncClient):
        async with self.__lock:
            if self._body and not self._serialized_body:
                self._serialized_body = orjson.dumps(self._body)
            if not self._before_scripts_done:
                for script in self._before_scripts:
                    await self.__exec_script(script)
                self._before_scripts_done = True
        if logger.isEnabledFor(10):  # nocov
            logger.debug('%s: %s%s p: %s|h: %s|b: %s|c: %s',
                self._method,
                self._base_url or client.base_url,
                self._url,
                self._params,
                self.get.sec_headers,
                self._body,
                self._cookies
            )
        response = await client.request(
            self._method,
            self._url,
            data=self._serialized_body,
            params=self._params,
            headers=self._headers,
            cookies=self._cookies,
        )
        if response.is_success:
            if self._after_scripts:
                await self.__exec_afterscripts(response)
            return response
        else:
            return response

    async def execute(self, client: AsyncClient = None):
        if not client:
            async with AsyncClient(base_url=self._base_url) as client:
                return await self.__execute(client)
        return await self.__execute(client)

    @property
    def get(self):
        return self.__ro

    def copy(self):
        inst = self.__class__(self.get.base_url)
        inst.method(self.get.method)\
            .url(self.get.url)\
            .params(self.get.params)\
            .headers(self.get.headers)\
            .cookies(self.get.cookies)\
            .body(self.get.body)\
            .retries(self.get.retries)
        inst._before_scripts = self._before_scripts.copy()
        inst._after_scripts = self._after_scripts.copy()
        return inst