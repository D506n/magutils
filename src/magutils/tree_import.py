import importlib as imp
from functools import lru_cache
from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)


@lru_cache(1)
def _get_root_path():
    root = Path(__file__).parent
    while 'pyproject.toml' not in [p.name for p in root.iterdir()]:
        root = root.parent
    return root


def _path_to_module(path: Path) -> str:
    root = _get_root_path()
    mod = path.relative_to(root)
    return str(mod)\
        .replace('/', '.')\
        .replace('\\', '.')\
        .replace('.py', '')


def _load_entity(
        subpath: Path, 
        subfolders: list[Path], 
        mod_name: str, 
        entity_type: type,
        skip_err: bool):
    entity = None
    if subpath.is_dir() and not subpath.name.startswith('_'):
        subfolders.append(subpath)
    module_path = _path_to_module(subpath)
    if subpath.is_file() and subpath.name == mod_name:
        module = imp.import_module(module_path)
        check = False
        for name in dir(module):
            if isinstance(getattr(module, name), entity_type):
                entity = getattr(module, name)
                check = True
        if check:
            logger.info(f'Found entity {module_path}')
        elif not skip_err:
            logger.error(f'Entity not found {module_path}')
            raise ModuleNotFoundError(f'Entity not found {module_path}')
        else:
            logger.warning(f'Entity not found {module_path}')
    elif subpath.is_file()\
            and subpath.name != '__init__.py'\
            and subpath.suffix == '.py':
        imp.import_module(module_path)
    return entity


def _build_branch(
        entity_type: type, 
        add_name: str, 
        mod_name: str,
        path: Path, 
        skip_err: bool = False):
    subfolders: list[Path] = []
    entity = None
    for subpath in path.iterdir():
        temp = _load_entity(
            subpath, subfolders, mod_name, entity_type, skip_err)
        if temp:
            entity = temp
    for subfolder in subfolders:
        sub_entity = _build_branch(
            entity_type, add_name, mod_name, subfolder, skip_err)
        if sub_entity:
            getattr(entity, add_name)(sub_entity)
    return entity


def build_root(
        entity_type: type, 
        root_path: Path, 
        mod_name: str, 
        add_name: str = 'load', 
        skip_err: bool = False, 
        **kwargs):
    if not isinstance(root_path, Path):
        root_path = Path(root_path).absolute()
    root = entity_type(**kwargs)
    for subpath in root_path.iterdir():
        if not subpath.is_dir():
            continue
        router = _build_branch(
            entity_type, add_name, mod_name, subpath, skip_err)
        if router:
            func = getattr(root, add_name)
            func(router)
    logger.info(f'Tree {entity_type.__name__} build setup done')
    return root


def build_root_fastapi(
        path: Path, file_name: str = 'api_router.py', skip_err: bool = False):
    try:
        from fastapi import APIRouter
    except ImportError:
        raise ImportError(
            'FastAPI not installed, use `uv add fastapi[standard]` to use it.')
    return build_root(
        APIRouter, path, file_name, add_name='include_router', skip_err=skip_err
    )


def build_root_telegrinder(
        path: Path, file_name: str = 'disp.py', skip_err: bool = False):
    try:
        from telegrinder import Dispatch
    except ImportError:
        raise ImportError(
            'Telegrinder not installed,'
            ' use `uv add telegrinder brotli` to use it.'
        )
    return build_root(
        Dispatch, path, file_name, add_name='load', skip_err=skip_err
    )
