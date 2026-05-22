import base64
import hashlib
import hmac
import os
import time
from logging import getLogger
from typing import TypedDict

import orjson

logger = getLogger(__name__)


class DecodeResult(TypedDict):
    headers: dict
    payload: dict
    signature: bytes


class ConfigMeta(type):
    _default_header = {"alg": "HS256", "typ": "JWT"}
    _precomp_header: str = None
    _hmac: hmac.HMAC = None
    _secret: str = None

    @property
    def secret(self):
        if self._secret is None:
            temp = os.getenv('JWT_SECRET')
            if not temp:
                raise KeyError('JWT secret not set!')
            self._secret = temp
        return self._secret

    @secret.setter
    def secret(self, value: str):
        if not isinstance(value, str):
            raise TypeError('secret must be a string')
        self._secret = value

    @property
    def default_header(self):
        return self._default_header

    @default_header.setter
    def default_header(self, value: dict):
        if not isinstance(value, dict):
            raise TypeError("default_header must be a dict")
        self._default_header = value
        self._precomp_header = None

    @property
    def precomp_header(self):
        if not self._precomp_header:
            self._precomp_header = base64.urlsafe_b64encode(
                orjson.dumps(self.default_header)).rstrip(b'=').decode()
        return self._precomp_header

    def hmac(self, secret: str):
        if not self._hmac or secret != self._secret:
            self._secret = secret
            self._hmac = hmac.new(secret.encode(), None, hashlib.sha256)
        return self._hmac.copy()


class Config(metaclass=ConfigMeta):
    pass


def jwt_encode(payload: dict, secret: str = None, headers: dict = None) -> str:
    if not secret:
        secret = Config.secret
    if headers:
        header = Config.default_header.copy()
        header.update(headers)
        h = base64.urlsafe_b64encode(orjson.dumps(header)).rstrip(b'=').decode()
    else:
        h = Config.precomp_header
    p = base64.urlsafe_b64encode(orjson.dumps(payload)).rstrip(b'=').decode()
    msg = f"{h}.{p}".encode()
    hm = Config.hmac(secret)
    hm.update(msg)
    sig = hm.digest()
    s = base64.urlsafe_b64encode(sig).rstrip(b'=').decode()
    return f"{h}.{p}.{s}"


def jwt_decode(token: str, secret: str = None) -> DecodeResult:
    if not secret:
        secret = Config.secret
    try:
        h, p, s = token.split('.')
        msg = f"{h}.{p}".encode()
        expected_sig = base64.urlsafe_b64decode(s + '==')
        hm = Config.hmac(secret)
        hm.update(msg)
        computed_sig = hm.digest()
        if not hmac.compare_digest(computed_sig, expected_sig):
            raise ValueError("invalid signature")
        curr = time.time()
        payload = orjson.loads(base64.urlsafe_b64decode(p + '=='))
        headers = orjson.loads(base64.urlsafe_b64decode(h + '=='))
        if payload.get("exp", curr) < curr:
            raise ValueError("expired")
        result = {
            'headers': headers, 'payload': payload, 'signature': expected_sig}
        return result
    except Exception as e:
        logger.error(e)
        raise ValueError(f'Invalid token: {e}')