import base64
import os
from functools import lru_cache, partial
from logging import getLogger
from typing import Any, Protocol

try:
    from kubernetes import client, config
    from kubernetes.client.models.v1_secret import V1Secret
except ImportError:
    raise ImportError(('Kubernetes is not installed!' 
         ' Run `pip install kubernetes` to get k8s sdk.'))

logger = getLogger(__file__)


class Factory(Protocol):
    def __call__(self, api: client.CoreV1Api, name: str, prefix: str) -> Any: ... # noqa


@lru_cache()
def get_k8s_client():
    try:
        config.load_incluster_config()
    except Exception as e:
        logger.warning(e)
        logger.info('Try load local config')
        try:
            config.load_kube_config()
        except Exception as e:
            logger.error(e)
    return client.CoreV1Api()


def __get_secret(api: client.CoreV1Api, name: str, space: str, key: str = None):
    try:
        data: V1Secret = api.read_namespaced_secret(name, space)
    except Exception as e:
        logger.warning(('Couldn\'t'
                f'access secret {space}:{name}.'
                f' Error: {e}'
                f'\nGet from env: {name}'))
    else:
        if key:
            try:
                result = data.data[key]
            except Exception as e:
                logger.error(e)
            else:
                return base64.b64decode(result).decode()
        else:
            return data.data
        return os.getenv(f'{name}')


def secret(
        namespace: str = 'default', 
        secret_name: str = None,
        no_prefix: bool = False) -> Factory:
    def factory(
            namespace: str, 
            secret_name: str | None, 
            no_prefix: bool, 
            api: client.CoreV1Api, 
            name: str, 
            prefix: str):
        if no_prefix:
            prefix = ''
        if secret_name:
            return __get_secret(api, secret_name, namespace, prefix + name)
        else:
            return __get_secret(api, prefix + name, namespace)
    return partial(factory, namespace, secret_name, no_prefix)