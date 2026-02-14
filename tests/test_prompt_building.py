import tempfile
from pathlib import Path

import orjson
import pytest

from src.prompt_building import PromptHelper


class TestPromptHelper:
    def test_singleton(self):
        a = PromptHelper()
        b = PromptHelper()
        assert a is b

    def test_paths(self):
        ph = PromptHelper()
        assert ph.path.exists()
        assert ph.path.is_dir()
        for k, f in ph.__dict__.items():
            if 'path' in k and isinstance(f, Path):
                assert f.exists()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "key, expected",
        [
            ('vacation_create', {"table":None,"api_schema":None,"example":"{\"date_from\":\"2020-01-01\",\"date_to\":\"2020-01-02\",\"comment\":\"Комментарий к запросу\",\"error\":\"Ошибка парсинга запроса(распиши что именно не получилось)\"}","rule":"{\"description\":\"Даты в вопросе пользователя могут быть в любом виде. При формировании ответа используй формат: YYYY-MM-DD\",\"date_from\":{\"description\":\"Дата начала отпуска.\"},\"date_to\":{\"description\":\"Дата окончания отпуска.\"},\"comment\":{\"description\":\"Комментарий к запросу\"}}","subject":None}) # noqa
        ]
    )
    async def test_get(self, key, expected):  # TODO: очень плохой тест, как и 
        # сам класс необходимо придумать более адекватный способ создания 
        # промтов и управления ими
        ph = PromptHelper()
        result = await ph.get(key)
        assert orjson.dumps(result, option=orjson.OPT_SORT_KEYS)\
        == orjson.dumps(expected, option=orjson.OPT_SORT_KEYS)

    def test_incorrect_folder(self):
        # TODO: очень плохой класс
        d = Path(__file__).parent.parent / 'prompt_building/rules'
        with tempfile.TemporaryDirectory(
                prefix='test_', 
                suffix='.json', 
                dir=d, 
                ignore_cleanup_errors=True) as td:
            for f in d.iterdir():
                print(f)
                print(f.is_file())
            with pytest.raises(ValueError, match='not a file'):
                ph = PromptHelper()
                ph.load_rules()