import pytest

from src.magutils.json_path.dict_to_path import dict_to_paths, Path


class TestPath:
    """Тесты для внутреннего класса Path."""

    def test_path_single_key(self):
        """Один ключ без детей — compile возвращает [key]."""
        p = Path("a")
        assert p.compile() == ["a"]

    def test_path_root_no_key_no_children(self):
        """Корневой Path без key и без детей — пустой список."""
        p = Path()
        assert p.compile() == []

    def test_path_nested_dict(self):
        """Вложенный словарь: a → b → c."""
        root = Path()
        a = Path("a", root)
        b = Path("b", a)
        Path("c", b)
        assert root.compile() == ["a.b.c"]

    def test_path_multiple_children(self):
        """Несколько детей у одного родителя."""
        root = Path()
        a = Path("a", root)
        Path("x", a)
        Path("y", a)
        assert sorted(root.compile()) == ["a.x", "a.y"]

    def test_path_deduplication(self):
        """compile дедуплицирует пути через dict.fromkeys."""
        root = Path()
        a = Path("a", root)
        Path("x", a)
        Path("x", a)
        assert root.compile() == ["a.x"]


class TestDictToPathsModeWild:
    """Режим 'wild' — списки схлопываются в *."""

    def test_empty_dict(self):
        assert dict_to_paths({}) == []

    def test_flat_dict(self):
        assert sorted(dict_to_paths({"a": 1, "b": 2})) == ["a", "b"]

    def test_nested_dict(self):
        assert dict_to_paths({"a": {"b": 1}}) == ["a.b"]

    def test_deeply_nested_dict(self):
        assert dict_to_paths({"a": {"b": {"c": {"d": 1}}}}) == ["a.b.c.d"]

    def test_multiple_branches(self):
        data = {"a": {"x": 1, "y": 2}, "b": {"z": 3}}
        assert sorted(dict_to_paths(data)) == ["a.x", "a.y", "b.z"]

    def test_list_wildcard(self):
        data = {"items": [{"id": 1}, {"id": 2}]}
        assert dict_to_paths(data) == ["items.*.id"]

    def test_list_of_lists(self):
        data = {"matrix": [[1, 2], [3, 4]]}
        assert dict_to_paths(data) == ["matrix.*.*"]

    def test_empty_list(self):
        data = {"items": []}
        assert dict_to_paths(data) == ["items.*"]

    def test_mixed_dict_list(self):
        data = {"config": {"users": [{"name": "Alice"}, {"name": "Bob"}], "version": 2}}
        assert sorted(dict_to_paths(data)) == ["config.users.*.name", "config.version"]

    def test_list_of_dicts_multiple_keys(self):
        data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        assert sorted(dict_to_paths(data)) == ["users.*.age", "users.*.name"]

    def test_nested_list_in_dict(self):
        data = {"groups": [{"tags": ["a", "b"]}]}
        assert dict_to_paths(data) == ["groups.*.tags.*"]

    def test_scalar_values(self):
        data = {"int": 1, "str": "hello", "bool": True, "none": None}
        assert sorted(dict_to_paths(data)) == ["bool", "int", "none", "str"]


class TestDictToPathsModeStrict:
    """Режим 'strict' — списки с числовыми индексами."""

    def test_list_strict_indices(self):
        data = {"items": [{"id": 1}, {"id": 2}]}
        assert dict_to_paths(data, mode="strict") == ["items.0.id", "items.1.id"]

    def test_list_of_lists_strict(self):
        data = {"matrix": [[1, 2], [3, 4]]}
        result = sorted(dict_to_paths(data, mode="strict"))
        assert result == ["matrix.0.0", "matrix.0.1", "matrix.1.0", "matrix.1.1"]

    def test_empty_list_strict(self):
        data = {"items": []}
        assert dict_to_paths(data, mode="strict") == ["items.*"]

    def test_mixed_dict_list_strict(self):
        data = {"config": {"users": [{"name": "Alice"}, {"name": "Bob"}], "version": 2}}
        result = sorted(dict_to_paths(data, mode="strict"))
        assert result == ["config.users.0.name", "config.users.1.name", "config.version"]

    def test_list_of_dicts_multiple_keys_strict(self):
        data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        result = sorted(dict_to_paths(data, mode="strict"))
        assert result == ["users.0.age", "users.0.name", "users.1.age", "users.1.name"]

    def test_nested_list_in_dict_strict(self):
        data = {"groups": [{"tags": ["a", "b"]}]}
        result = sorted(dict_to_paths(data, mode="strict"))
        assert result == ["groups.0.tags.0", "groups.0.tags.1"]

    def test_flat_dict_strict(self):
        """Плоский словарь — режим strict не влияет."""
        assert sorted(dict_to_paths({"a": 1, "b": 2}, mode="strict")) == ["a", "b"]


class TestDictToPathsModeFull:
    """Режим 'full' — каждый элемент списка через *, пути дублируются."""

    def test_list_full_duplicates(self):
        """Каждый элемент порождает * — пути дублируются, но compile дедуплицирует."""
        data = {"items": [{"id": 1}, {"id": 2}]}
        assert dict_to_paths(data, mode="full") == ["items.*.id"]

    def test_list_of_lists_full(self):
        data = {"matrix": [[1, 2], [3, 4]]}
        assert dict_to_paths(data, mode="full") == ["matrix.*.*"]

    def test_empty_list_full(self):
        data = {"items": []}
        assert dict_to_paths(data, mode="full") == ["items.*"]

    def test_mixed_dict_list_full(self):
        data = {"config": {"users": [{"name": "Alice"}, {"name": "Bob"}], "version": 2}}
        assert sorted(dict_to_paths(data, mode="full")) == ["config.users.*.name", "config.version"]

    def test_list_of_dicts_multiple_keys_full(self):
        data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        assert sorted(dict_to_paths(data, mode="full")) == ["users.*.age", "users.*.name"]

    def test_nested_list_in_dict_full(self):
        data = {"groups": [{"tags": ["a", "b"]}]}
        assert dict_to_paths(data, mode="full") == ["groups.*.tags.*"]

    def test_flat_dict_full(self):
        """Плоский словарь — режим full не влияет."""
        assert sorted(dict_to_paths({"a": 1, "b": 2}, mode="full")) == ["a", "b"]


class TestDictToPathsEdgeCases:
    """Краевые случаи для всех режимов."""

    @pytest.mark.parametrize("mode", ["wild", "strict", "full"])
    def test_empty_dict_all_modes(self, mode):
        assert dict_to_paths({}, mode=mode) == []

    @pytest.mark.parametrize("mode", ["wild", "strict", "full"])
    def test_single_key_all_modes(self, mode):
        assert dict_to_paths({"a": 1}, mode=mode) == ["a"]

    @pytest.mark.parametrize("mode", ["wild", "strict", "full"])
    def test_nested_dict_all_modes(self, mode):
        assert dict_to_paths({"a": {"b": {"c": 1}}}, mode=mode) == ["a.b.c"]

    @pytest.mark.parametrize("mode", ["wild", "strict", "full"])
    def test_scalar_values_all_modes(self, mode):
        data = {"int": 1, "str": "hello", "bool": True, "none": None}
        assert sorted(dict_to_paths(data, mode=mode)) == ["bool", "int", "none", "str"]

    def test_deep_branching(self):
        """Глубокое ветвление с разными типами."""
        data = {
            "a": {
                "b": [{"c": 1, "d": 2}],
                "e": {"f": 3},
            }
        }
        result = sorted(dict_to_paths(data, mode="strict"))
        assert result == ["a.b.0.c", "a.b.0.d", "a.e.f"]

    def test_list_of_lists_different_lengths(self):
        """Список списков разной длины — strict."""
        data = {"m": [[1], [2, 3]]}
        result = sorted(dict_to_paths(data, mode="strict"))
        assert result == ["m.0.0", "m.1.0", "m.1.1"]

    def test_list_of_lists_different_lengths_wild(self):
        """Список списков разной длины — wild."""
        data = {"m": [[1], [2, 3]]}
        assert dict_to_paths(data, mode="wild") == ["m.*.*"]

    def test_list_of_lists_different_lengths_full(self):
        """Список списков разной длины — full."""
        data = {"m": [[1], [2, 3]]}
        assert dict_to_paths(data, mode="full") == ["m.*.*"]