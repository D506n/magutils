import orjson
import pytest

from src.utils.json_path import format, get_by_path, set_by_path


class TestJsonPath:
    @pytest.mark.parametrize(
            "data, path, expected",
            [
                ({"a": 1}, 'a', 1),
                ({"a": {"b": 2}}, 'a.b', 2),
                ({"a": {"b": [3, 4, 5]}}, 'a.b.1', 4),
                ({"a": {"b": [{"c": 6}, 7, 8]}}, 'a.b.0.c', 6),
                ({"a": {"b": [{"c": 6}, 7, 8]}}, 'a.b.-1', 8)
            ]
    )
    def test_get_by_path(self, data, path, expected):
        assert get_by_path(data, path) == expected

    def test_get_by_path_raises_error(self):
        data = {'a': 1}
        with pytest.raises(KeyError):
            get_by_path(data, 'b')

    @pytest.mark.parametrize(
            "data, path, toset, expected",
            [
                ({"a": 1}, 'b', 2, orjson.dumps({"a": 1, "b": 2})),
                ({"a": {"b": 2}}, 'a.c', 3, orjson.dumps({"a": {"b": 2, "c": 3}})), # noqa
                ({"a": {"b": [4, 5]}}, 'a.b.1', 6, orjson.dumps({"a": {"b": [4, 6]}})), # noqa
                ({"a": {"b": [{"c": 6}, 7, 8]}}, 'a.b.0.c', 9, orjson.dumps({"a": {"b": [{"c": 9}, 7, 8]}})), # noqa
                ({'a': [0]}, 'a.!a', 1, orjson.dumps({'a': [0, 1]})),
                ({'a': []}, 'a.!a.!a', 1, orjson.dumps({'a': [[1]]})),
                ({"a": 1}, 'b.!a', 2, orjson.dumps({"a": 1, "b": [2]})),
                ({}, 'a.b', 1, orjson.dumps({"a": {"b": 1}})),
                ({"a": []}, 'a.!a.b', 1, orjson.dumps({"a": [{"b": 1}]}))
            ]
    )
    def test_set_by_path(self, data, path, toset, expected):
        set_by_path(data, path, toset)
        assert orjson.dumps(data) == expected

    def test_set_by_path_raises_error(self):
        data = {'a': {'b': []}}
        with pytest.raises(KeyError):
            set_by_path(data, 'a.b.1', 10)

    @pytest.mark.parametrize(
            'string, data, expected',
            [
                ('Test {a}', {'a': 1}, 'Test 1'),
                ('Test {a.b}', {'a': {'b': 2}}, 'Test 2'),
                ('Test {a.b.1}', {'a': {'b': [3, 3, 5]}}, 'Test 3'),
                ('Test {a.b.0.c}', {'a': {'b': [{'c': 4}, 7, 8]}}, 'Test 4'),
                ('Test {a.b.-1}', {'a': {'b': [{'c': 4}, 7, 5]}}, 'Test 5')
            ]
    )
    def test_format(self, string, data, expected):
        result = format(string, data)
        assert result == expected