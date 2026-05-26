import pytest

from src.magutils.json_path import get_by_path, set_by_path, del_by_path, rebuild, deepmerge
from src.magutils.json_path.walker import StopWalk


class TestJsonPath:
    """Тесты для модуля json_path."""

    def test_get_by_path_simple_dict(self):
        data = {"a": {"b": {"c": 42}}}
        assert get_by_path("a.b.c", data) == [42]

    def test_get_by_path_with_default(self):
        data = {"a": {"b": {}}}
        assert get_by_path("a.b.c", data, default=100) == [100]

    def test_get_by_path_silent_false_raises(self):
        data = {"a": {"b": {}}}
        with pytest.raises(StopWalk):
            get_by_path("a.b.c.d", data, silent=False)

    def test_get_by_path_list_index(self):
        data = {"items": [{"id": 1}, {"id": 2}]}
        assert get_by_path("items.0.id", data) == [1]
        assert get_by_path("items.1.id", data) == [2]

    def test_get_by_path_wildcard(self):
        data = {"items": [{"id": 1}, {"id": 2}]}
        result = get_by_path("items.*.id", data)
        assert result == [1, 2]

    def test_set_by_path_simple_dict(self):
        data = {"a": {"b": {}}}
        set_by_path("a.b.c", data, 99)
        assert data == {"a": {"b": {"c": 99}}}

    def test_set_by_path_create_missing(self):
        data = {}
        set_by_path("x.y.z", data, "value")
        assert data == {"x": {"y": {"z": "value"}}}

    def test_set_by_path_list_append(self):
        data = {"list": []}
        set_by_path("list.!a", data, "new")
        assert data == {"list": ["new"]}

    def test_set_by_path_list_index(self):
        data = {"list": ["a", "b", "c"]}
        set_by_path("list.1", data, "B")
        assert data == {"list": ["a", "B", "c"]}

    def test_del_by_path_simple(self):
        data = {"a": {"b": {"c": 42}}}
        del_by_path("a.b.c", data)
        assert data == {"a": {"b": {}}}

    def test_del_by_path_list_index(self):
        data = {"list": ["x", "y", "z"]}
        del_by_path("list.1", data)
        assert data == {"list": ["x", "z"]}

    def test_del_by_path_wildcard(self):
        data = {"items": [{"id": 1}, {"id": 2}]}
        del_by_path("items.*.id", data)
        assert data == {"items": [{}, {}]}

    def test_rebuild_simple(self):
        data = {"source": {"value": 5}}
        result = rebuild("source.value->target", data=data)
        assert result == {"target": 5}

    def test_rebuild_multiple_paths(self):
        data = {"a": 1, "b": 2}
        result = rebuild("a->x", "b->y", data=data)
        assert result == {"x": 1, "y": 2}

    def test_rebuild_wildcard(self):
        data = {"items": [{"id": 10}, {"id": 20}]}
        result = rebuild("items.*.id-> *.id", data=data)
        assert result == [{"id": 10}, {"id": 20}]

    def test_deepmerge_basic(self):
        old = {"a": 1, "b": {"c": 2}}
        new = {"b": {"d": 3}, "e": 4}
        merged = deepmerge(old, new)
        assert merged == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        # оригинал не изменён
        assert old == {"a": 1, "b": {"c": 2}}

    def test_deepmerge_overwrite(self):
        old = {"a": 1, "b": {"c": 2}}
        new = {"b": {"c": 99}}
        merged = deepmerge(old, new)
        assert merged == {"a": 1, "b": {"c": 99}}

    def test_deepmerge_nested_dict(self):
        old = {"x": {"y": {"z": 1}}}
        new = {"x": {"y": {"w": 2}}}
        merged = deepmerge(old, new)
        assert merged == {"x": {"y": {"z": 1, "w": 2}}}

    def test_deepmerge_empty_new(self):
        old = {"a": 1}
        new = {}
        merged = deepmerge(old, new)
        assert merged == {"a": 1}

    def test_deepmerge_empty_old(self):
        old = {}
        new = {"a": 1}
        merged = deepmerge(old, new)
        assert merged == {"a": 1}