import json
import pytest

from generative_agents.modules.utils.arguments import load_dict, update_dict, dump_dict, dict_equal


def test_load_dict_invalid_type_raises():
    with pytest.raises(Exception):
        load_dict(123)  # not str or dict


def test_update_dict_type_mismatch_raises():
    with pytest.raises(AssertionError):
        update_dict({"a": 1}, [1,2,3])


def test_dump_dict_table_and_json_flavors():
    data = {"a": {"b": [1, {"c": 2}]}}
    t = dump_dict(data, flavor="table:4")
    assert isinstance(t, str) and 'a' in t
    j = dump_dict(data, flavor="json")
    assert json.loads(j)["a"]["b"][1]["c"] == 2


def test_dict_equal_non_dict_returns_false():
    assert dict_equal({"a":1}, [1,2]) is False
