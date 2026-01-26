from logging import getLogger
from pathlib import Path
from typing import Callable

import orjson
import yaml
from babel.plural import to_python

from .json_path import get_by_path
from .singleton import singleton
from .time_utils import get_current_time, get_delta

TVALIDATOR = Callable[[dict, Path], bool]
pluralizer = Callable[[int], str]

logger = getLogger(__file__)


@singleton
class I18n:
    YAML_SUF = {'.yaml', '.yml'}
    ALL_FMTS = {'.json', '.yaml', '.yml'}

    def __init__(self, 
                        locdir: Path | str, 
                        falllang: str = None,
                        custom_validators: list[TVALIDATOR] = None,
                        scan_ttl: float = 60.0,
                        plural_rules_path: Path = None,
                        strict: bool = False):
        if not isinstance(locdir, Path):
            locdir = Path(locdir)
        if not locdir.is_dir():
            raise ValueError('Locdir must be directory!')
        if not plural_rules_path:
            plural_rules_path = Path(__file__).parent / 'plurals.json'
        self.plural_rules_path = plural_rules_path
        self.locdir = locdir
        self.custom_validators = custom_validators or []
        self.dictionaries, self.pluralizers = self.scan_dir()
        if not self.dictionaries:
            raise FileNotFoundError('Translation files not found in %s', locdir)
        self.falllang = falllang or list(self.dictionaries.keys())[0]
        self.scan_ttl = scan_ttl
        self.strict = strict

    def __check_translation(self, data: dict, file: Path):
        if not isinstance(data, dict):
            logger.error('Incorrect translation file format: %s', file)
        else:
            return True
        return False

    def __load_json(self, file: Path):
        with file.open('r', encoding='utf-8') as f:
            try:
                data = orjson.loads(f.read())
            except orjson.JSONDecodeError as e:
                logger.error(
                    'Translation file parsing error: %s, %s', 
                    file, 
                    e
                )
            if self.__check_translation(data, file):
                return data
        return

    def __load_yaml(self, file: Path):
        with file.open('r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f.read())
            except yaml.error.YAMLError as e:
                logger.error('Translation file parsing error: %s, %s', file, e)
            if self.__check_translation(data, file):
                return data
            return

    def scan_dir(self):
        self.last_scan = get_current_time()
        dicts: dict = {}
        plurs: dict[str, pluralizer] = {}
        with open(self.plural_rules_path, 'r', encoding='utf-8') as f: 
            raw_plural_rules = orjson.loads(f.read())
        for file in self.locdir.iterdir():
            if file.suffix not in self.ALL_FMTS:
                logger.warning('Unsupported file format: %s', file)
                continue
            if not file.is_file():
                continue
            data = None
            if file.suffix == '.json':
                data = self.__load_json(file)
            elif file.suffix in self.YAML_SUF:
                data = self.__load_yaml(file)
            if data:
                dicts[file.stem] = data
                plurs[file.stem] = to_python(raw_plural_rules[file.stem])
        return dicts, plurs

    def __check_lang(self, lang: str):
        if not lang:
            lang = self.falllang
        elif lang not in self.dictionaries.keys():
            logger.warning('Language not found: %s', lang)
            if get_delta(self.last_scan).total_seconds() > self.scan_ttl:
                self.dictionaries = self.scan_dir()
            if lang not in self.dictionaries.keys():
                lang = self.falllang
        return lang

    def t(self, key: str, lang: str = None, **kwargs):
        lang = self.__check_lang(lang)

        text_obj = get_by_path(self.dictionaries[lang], key)

        if isinstance(text_obj, str):
            return text_obj.format(**kwargs)

        if isinstance(text_obj, dict):
            text_obj: dict[str, str]
            count_key = self.pluralizers[lang](kwargs.get('count', 1))
            if count_key in text_obj.keys():
                return text_obj[count_key].format(**kwargs)

        err = f'{lang}:{key}[{kwargs.get("count", "")}:{count_key or ""}]'
        if self.strict:
            raise KeyError('Translation not found: %s', err)
        return err
