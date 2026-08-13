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


class _I18n:
    YAML_SUF = {'.yaml', '.yml'}
    ALL_FMTS = {'.json', '.yaml', '.yml'}

    def __init__(self, 
                        locdir: Path | str = '',
                        custom_validators: list[TVALIDATOR] = None,
                        scan_ttl: float = 60.0,
                        plural_rules_path: Path = None):
        if not locdir:
            raise ValueError("Locdir must be provided for first call!")
        if not isinstance(locdir, Path):
            locdir = Path(locdir)
        if not locdir.is_dir():
            raise ValueError('Locdir must be directory!')
        if not plural_rules_path:
            plural_rules_path = Path(__file__).parent / 'plurals.json'
        self.plural_rules_path = plural_rules_path
        self.locdir = locdir
        self.custom_validators = custom_validators or []  # пока не работает
        self.dictionaries, self.pluralizers = self.scan_dir()
        if not self.dictionaries:
            raise FileNotFoundError('Translation files not found in %s', locdir)
        self.scan_ttl = scan_ttl
        self.__curr_lang: str = ''

    @property
    def current_lang(self):
        return self.__curr_lang

    @current_lang.setter
    def current_lang(self, lang: str):
        self.__curr_lang = self.__check_lang(lang)

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
                return
            if self.__check_translation(data, file):
                return data
        return

    def __load_yaml(self, file: Path):
        with file.open('r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f.read())
            except yaml.error.YAMLError as e:
                logger.error('Translation file parsing error: %s, %s', file, e)
                return
            if self.__check_translation(data, file):
                return data

    def scan_dir(self):
        self.last_scan = get_current_time()
        dicts: dict = {}
        plurs: dict[str, pluralizer] = {}
        with open(self.plural_rules_path, 'r', encoding='utf-8') as f: 
            raw_plural_rules = orjson.loads(f.read())
        for file in self.locdir.iterdir():
            if file.stem == self.plural_rules_path.stem:
                continue
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
                if file.stem not in raw_plural_rules.keys():
                    raise ValueError(
                        f'Plural rules not found for language: {file.stem}')
                if not isinstance(raw_plural_rules[file.stem], dict):
                    raise ValueError('Plural rules must be a dictionary')
                plurs[file.stem] = to_python(raw_plural_rules[file.stem])
        return dicts, plurs

    def __check_lang(self, lang: str):
        if lang not in self.dictionaries.keys():
            logger.warning(f'Language not found: {lang}')
            if get_delta(self.last_scan).total_seconds() > self.scan_ttl:
                self.dictionaries, self.pluralizers = self.scan_dir()
            if lang not in self.dictionaries.keys():
                raise KeyError(f'Language not found: {lang}')
        return lang

    def __obj_processing(self, 
                         text_obj: str | dict, 
                         key: str,
                         lang: str, 
                         **kwargs):
        err_text = f'{lang}:{key}'
        if text_obj:
            text_obj = text_obj[0]
        else:
            raise KeyError(err_text)

        if isinstance(text_obj, str):
            return text_obj.format(**kwargs)

        if isinstance(text_obj, dict):
            text_obj: dict[str, str]
            count_key = self.pluralizers[lang](kwargs.get('count', 1))
            err_text += f'[{kwargs.get("count", "")}:{count_key or ""}]'

            if count_key in text_obj.keys():
                return text_obj[count_key].format(**kwargs)
        raise KeyError(err_text)

    def t(self, 
            key: str, 
            lang: str = None, 
            fallback: str = None, 
            strict: bool = False, 
            **kwargs):
        if lang is None:
            if curr := self.current_lang:
                lang = curr
            else:
                lang = list(self.dictionaries.keys())[0]
        try:
            self.__check_lang(lang)
            text_obj = get_by_path(key, self.dictionaries[lang])
            result = self.__obj_processing(text_obj, key, lang, **kwargs)
        except KeyError as e:
            if fallback:
                return fallback.format(**kwargs)
            elif strict:
                raise KeyError(f'Translation not found: {e}')
            else:
                return e.args[0]
        return result


@singleton
class I18n(_I18n):
    pass


def text(
        key: str, 
        lang: str = None, 
        fallback: str = None, 
        strict: bool = False, 
        **kwargs
) -> str:
    '''Обёртка для отложенного вызова.'''
    inst = I18n()
    return inst.t(key, lang, fallback, strict, **kwargs)