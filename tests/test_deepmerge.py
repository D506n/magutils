from copy import deepcopy
from typing import Any, Literal, cast

import pytest

from src.magutils.json_path import deepmerge


@pytest.mark.parametrize(('old', 'new', 'expected'), [
    ({'rows': ['old']}, {'rows': ['new']}, {'rows': ['new']}),
    (
        {'items': [{'a': 1}, 'old']},
        {'items': [{'b': 2}, 'new', 'added']},
        {'items': [{'a': 1, 'b': 2}, 'new', 'added']},
    ),
    ({'items': [1, 2, 3]}, {'items': [4]}, {'items': [4, 2, 3]}),
    ({'items': [1, 2]}, {'items': []}, {'items': [1, 2]}),
    ({'items': [[1, 2]]}, {'items': [[3]]}, {'items': [[3, 2]]}),
    ({'value': 1}, {'value': {'x': 2}}, {'value': {'x': 2}}),
    ({'value': {'x': 1}}, {'value': 2}, {'value': 2}),
    ({'value': [1]}, {'value': {'x': 2}}, {'value': {'x': 2}}),
    ({'value': {'x': 1}}, {'value': [2]}, {'value': [2]}),
    ({'value': {1, 2}}, {'value': {3}}, {'value': {3}}),
    ({'value': [1, 2]}, {'value': {3}}, {'value': {3}}),
    ({'value': {1, 2}}, {'value': [3]}, {'value': [3]}),
])
def test_merge_values(old: dict, new: dict, expected: dict) -> None:
    before_old, before_new = deepcopy(old), deepcopy(new)
    assert deepmerge(old, new) == expected
    assert old == before_old
    assert new == before_new


@pytest.mark.parametrize('replacement', [[], ['new'], [{'b': 2}], [None, {'x': None}]])
def test_replace_lists(replacement: list[Any]) -> None:
    old = {'nested': {'items': [{'a': 1}, 'tail'], 'keep': True}}
    new = {'nested': {'items': replacement}}
    result = deepmerge(old, new, list_strategy='replace', delete_none=True)
    assert result == {'nested': {'items': replacement, 'keep': True}}
    assert result['nested']['items'] is not replacement


def test_none_is_preserved_by_default() -> None:
    assert deepmerge({'a': 1}, {'a': None, 'b': None}) == {'a': None, 'b': None}


def test_none_deletes_keys_recursively_and_ignores_absent_keys() -> None:
    old = {'headers': {'Authorization': 'old', 'Accept': 'json'}, 'replace': 1}
    patch = {
        'headers': {'Authorization': None, 'Missing': None},
        'replace': {'removed': None, 'keep': 2},
        'new': {'removed': None, 'keep': 3},
        'absent': None,
    }
    assert deepmerge(old, patch, delete_none=True) == {
        'headers': {'Accept': 'json'}, 'replace': {'keep': 2}, 'new': {'keep': 3},
    }
    assert patch['headers']['Authorization'] is None
    assert old['headers']['Authorization'] == 'old'


def test_none_in_merged_list_preserves_position() -> None:
    old = {'items': [{'remove': 1, 'keep': 2}, 'old', 'tail']}
    patch = {'items': [{'remove': None}, None]}
    assert deepmerge(old, patch, delete_none=True) == {
        'items': [{'keep': 2}, None, 'tail'],
    }


def test_empty_patch_preserves_values_and_empty_mapping_replaces_scalar() -> None:
    assert deepmerge({'a': None}, {}, delete_none=True) == {'a': None}
    assert deepmerge({'a': 1}, {'a': {}}, delete_none=True) == {'a': {}}
    assert deepmerge({'a': {'b': 1}}, {'a': {}}) == {'a': {'b': 1}}


@pytest.mark.parametrize('copy_old', [True, False])
@pytest.mark.parametrize('strategy', ['merge', 'replace'])
def test_inserted_values_do_not_share_mutable_objects(
        copy_old: bool, strategy: Literal['merge', 'replace']) -> None:
    old = {'items': [{'existing': 1}]}
    patch = {'items': [{'nested': [1]}, {'added': []}], 'flags': {'new'}}
    before_patch = deepcopy(patch)
    result = deepmerge(old, patch, copy_old, list_strategy=strategy)
    result['items'][0]['nested'].append(2)
    result['items'][1]['added'].append(3)
    result['flags'].add('changed')
    assert patch == before_patch
    if copy_old:
        assert old == {'items': [{'existing': 1}]}
    else:
        assert result is old


def test_in_place_merge_preserves_existing_containers() -> None:
    nested = {'a': 1}
    items = [{'a': 1}]
    old = {'nested': nested, 'items': items}
    result = deepmerge(old, {'nested': {'b': 2}, 'items': [{'b': 2}]}, False)
    assert result is old
    assert result['nested'] is nested
    assert result['items'] is items
    assert nested == {'a': 1, 'b': 2}
    assert items == [{'a': 1, 'b': 2}]


def test_invalid_strategy_does_not_mutate_old() -> None:
    old = {'value': 1}
    invalid = cast(Literal['merge', 'replace'], 'append')
    with pytest.raises(ValueError, match='list_strategy'):
        deepmerge(old, {'value': 2}, False, list_strategy=invalid)
    assert old == {'value': 1}
