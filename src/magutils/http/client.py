from aiolimiter import AsyncLimiter
from httpx import AsyncClient, Limits, Timeout

from magutils.req_limit import Limiter

DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)
DEFAULT_LIMITS = Limits(max_connections=100, max_keepalive_connections=20)
DEFAULT_MAX_REDIRECTS = 20


class LimitAwareClient(AsyncClient):
    def __init__(self, *, 
            auth=None,
            params=None, 
            headers=None, 
            cookies=None, 
            verify=True, 
            cert=None, 
            http1=True, 
            http2=False, 
            proxy=None, 
            mounts=None, 
            timeout=DEFAULT_TIMEOUT_CONFIG, 
            follow_redirects=False, 
            limits=DEFAULT_LIMITS, 
            max_redirects=DEFAULT_MAX_REDIRECTS, 
            event_hooks=None, 
            base_url="", 
            transport=None, 
            trust_env=True, 
            default_encoding="utf-8",
            limiter: AsyncLimiter = None):
        super().__init__(
            auth=auth,
            params=params, 
            headers=headers, 
            cookies=cookies, 
            verify=verify, 
            cert=cert, 
            http1=http1, 
            http2=http2, 
            proxy=proxy, 
            mounts=mounts, 
            timeout=timeout, 
            follow_redirects=follow_redirects, 
            limits=limits, 
            max_redirects=max_redirects, 
            event_hooks=event_hooks, 
            base_url=base_url, 
            transport=transport, 
            trust_env=trust_env, 
            default_encoding=default_encoding
        )
        self.aiolimiter = limiter

    def __get_limiter(self):
        return self.aiolimiter or Limiter.get(self.base_url)

    async def send(
            self, 
            request, 
            *, 
            stream=False, 
            auth=..., 
            follow_redirects=...):
        async with self.__get_limiter():
            return await super().send(
                request, 
                stream=stream, 
                auth=auth, 
                follow_redirects=follow_redirects
            )