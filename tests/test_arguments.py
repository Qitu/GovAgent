import json
from pathlib import Path

import pytest

from generative_agents.modules.utils.arguments import (
    load_dict,
    save_dict,
    update_dict,
    dump_dict,
    dict_equal,
    copy_dict,
    map_dict,
)


def test_load_dict_from_string_json():
    # Should parse a JSON string into a dict
    data = {"a": 1, "b": {"c": 2}}
    assert load_dict(json.dumps(data)) == data


def test_load_dict_from_path(tmp_path: Path):
    # Should load JSON from a file path
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    assert load_dict(str(p)) == {"x": 1}


def test_load_dict_from_dict_and_copy():
    # Should deep-copy dict input (no reference sharing)
    src = {"k": [1, {"m": 2}]}
    out = load_dict(src)
    assert out == src
    out["k"][1]["m"] = 3
    assert src["k"][1]["m"] == 2  # original not mutated


def test_save_dict_roundtrip(tmp_path: Path):
    # Should save dict and be loadable back identically
    p = tmp_path / "out.json"
    data = {"foo": {"bar": True}}
    save_dict(data, str(p))
    assert load_dict(str(p)) == data


def test_update_dict_force_overwrite():
    # Force overwrite should replace existing keys and merge nested dicts
    src = {"a": 1, "b": {"x": 1, "y": 1}}
    new = {"a": 2, "b": {"x": 9}, "c": 3}
    out = update_dict(src, new, soft_update=False)
    assert out == {"a": 2, "b": {"x": 9, "y": 1}, "c": 3}


def test_update_dict_soft_update():
    # Soft update should only add missing keys and recurse for dict
    src = {"a": 1, "b": {"x": 1}}
    new = {"a": 2, "b": {"y": 2}}
    out = update_dict(src, new, soft_update=True)
    assert out == {"a": 1, "b": {"x": 1, "y": 2}}


def test_dump_dict_formats():
    # dump_dict should return non-empty string for non-empty dict in table flavor
    txt = dump_dict({"k": {"m": 1}}, flavor="table:2")
    assert isinstance(txt, str) and len(txt) > 0
    # JSON flavor should be valid JSON
    js = dump_dict({"k": 1}, flavor="json")
    assert json.loads(js) == {"k": 1}


def test_dict_equal():
    # dict_equal should consider structure and types
    a = {"k": {"m": 1}}
    b = {"k": {"m": 1}}
    c = {"k": {"m": "1"}}
    assert dict_equal(a, b)
    assert not dict_equal(a, c)


def test_copy_dict_deepcopy():
    # copy_dict should deep-copy nested structures
    a = {"k": [1, {"m": 2}]}
    b = copy_dict(a)
    assert a == b and a is not b
    b["k"][1]["m"] = 3
    assert a["k"][1]["m"] == 2


def test_map_dict_mapper_is_applied():
    # map_dict should apply mapper to values recursively
    def mapper(v):
        return v * 2 if isinstance(v, int) else v

    a = {"k": [1, {"m": 2}], "z": 3}
    out = map_dict(a, mapper)
    assert out == {"k": [2, {"m": 4}], "z": 6}
