import importlib as imp
from logging import getLogger
from pathlib import Path

from fastapi import APIRouter

logger = getLogger(__name__)


class SubMod:
    router: APIRouter


def _build_subrouter(path: Path, skip_err: bool = False):
    subfolders: list[Path] = []
    router: APIRouter = None
    for subpath in path.iterdir():
        if subpath.is_dir() and not subpath.name.startswith('_'):
            subfolders.append(subpath)
            continue
        module_path = '.'.join(subpath.relative_to(Path.cwd()).parts)\
            .replace('.py', '')
        if subpath.is_file() and subpath.name == 'api_router.py':
            module: SubMod = imp.import_module(module_path)
            if hasattr(module, 'router'):
                router = module.router
                logger.info(f'Found router {module_path}')
            elif not skip_err:
                logger.error(f'Router not found {module_path}')
                raise ModuleNotFoundError(f'Router not found {module_path}')
            else:
                logger.warning(f'Router not found {module_path}')
        elif subpath.is_file()\
                and subpath.name != '__init__.py'\
                and subpath.suffix == '.py':
            mod = imp.import_module(module_path)  # инициализация всех хендлеров
            if hasattr(mod, 'router'):  # если подгрузится файл с хендлерами
                logger.info(f'Handlers found: {module_path}')
    for subfolder in subfolders:
        router.include_router(_build_subrouter(subfolder, skip_err))
    return router


def build_root_router(skip_err: bool = False, **kwargs):
    root = APIRouter(**kwargs)
    path = Path(__file__).parent
    for subpath in path.iterdir():
        if not subpath.is_dir():
            continue
        router = _build_subrouter(subpath, skip_err)
        if router:
            root.include_router(router)
    logger.info('Root router setup done')
    return root
