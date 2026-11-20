"""Tests for 04_java_to_python/05_exceptions.ipynb

Run: pytest tests/java_to_python/test_04_05_exceptions.py -v
"""
import pytest

from labkit.testing import load

nb = load("04_java_to_python/05_exceptions.ipynb")


def test_load_json_config(tmp_path):
    assert nb.load_json_config(tmp_path / "nope.json") == {}
    good = tmp_path / "good.json"; good.write_text('{"a": 1}')
    assert nb.load_json_config(good) == {"a": 1}
    bad = tmp_path / "bad.json"; bad.write_text('{"a": ')
    with pytest.raises(ValueError, match="bad.json") as info:
        nb.load_json_config(bad)
    import json
    assert isinstance(info.value.__cause__, json.JSONDecodeError)
    lst = tmp_path / "list.json"; lst.write_text("[1]")
    with pytest.raises(ValueError):
        nb.load_json_config(lst)


def test_fetch_with_fallback():
    def ok(): return 1
    def down(): raise ConnectionError("db down")
    def slow(): raise TimeoutError("slow")
    def bug(): raise KeyError("oops")
    assert nb.fetch_with_fallback(ok, lambda: 2) == (1, "primary")
    assert nb.fetch_with_fallback(down, lambda: 2) == (2, "fallback")
    assert nb.fetch_with_fallback(slow, lambda: 3) == (3, "fallback")
    with pytest.raises(KeyError):
        nb.fetch_with_fallback(bug, lambda: 2)

def test_fetch_with_fallback_both_fail_keeps_context():
    class CacheDown(Exception):
        pass
    def down(): raise ConnectionError("primary down")
    def also_down(): raise CacheDown("cache down")
    fetch_with_fallback = nb.fetch_with_fallback
    with pytest.raises(CacheDown) as info:
        fetch_with_fallback(down, also_down)
    assert isinstance(info.value.__context__, ConnectionError)


def _v(r):
    if r.get("qty", 0) <= 0:
        raise ValueError(f"bad qty {r.get('qty')}")

def test_validate_or_raise_ok():
    rs = [{"qty": 1}]
    assert nb.validate_or_raise(rs, _v) is rs

def test_validate_or_raise_group():
    with pytest.raises(ExceptionGroup) as info:
        nb.validate_or_raise([{"qty": 1}, {"qty": 0}, {}, {"qty": 2}], _v)
    eg = info.value
    assert len(eg.exceptions) == 2 and "2 invalid" in str(eg)
    assert eg.exceptions[0].__notes__ == ["record index 1"] and eg.exceptions[1].__notes__ == ["record index 2"]

def test_validate_or_raise_other_errors_propagate():
    def boom(r): raise KeyError("x")
    with pytest.raises(KeyError):
        nb.validate_or_raise([{}], boom)

def test_except_star_usage():
    handled = []
    try:
        nb.validate_or_raise([{}], _v)
    except* ValueError as eg:
        handled.extend(eg.exceptions)
    assert len(handled) == 1


def test_load_records_ok(tmp_path):
    p = tmp_path / "r.json"; p.write_text('[{"a": 1}]')
    assert nb.load_records(p) == [{"a": 1}]

@pytest.mark.parametrize("content, message", [(None, "not found"), (b"\xff\xfe\x00bad", "encoding error"), (b"[{", "corrupt"),
                                              (b'{"a": 1}', "corrupt"), (b"[1, 2]", "corrupt")])
def test_load_records_errors(tmp_path, content, message):
    p = tmp_path / "r.json"
    if content is not None:
        p.write_bytes(content)
    with pytest.raises(nb.StorageError, match=message) as info:
        nb.load_records(p)
    assert info.value.path == str(p)
    if content is None or message != "corrupt" or content == b"[{":
        assert info.value.__cause__ is not None

def test_load_records_directory_is_oserror(tmp_path):
    with pytest.raises(nb.StorageError, match="cannot read"):
        nb.load_records(tmp_path)


def test_write_json_atomic(tmp_path):
    target = tmp_path / "sub" / "state.json"
    nb.write_json_atomic(target, {"v": 1})
    import json
    assert json.loads(target.read_text()) == {"v": 1}
    nb.write_json_atomic(target, {"v": 2})
    assert json.loads(target.read_text()) == {"v": 2}

def test_write_json_atomic_failure_keeps_original(tmp_path):
    target = tmp_path / "state.json"
    nb.write_json_atomic(target, {"v": 1})
    with pytest.raises(TypeError):
        nb.write_json_atomic(target, {"v": object()})
    assert target.read_text().replace(" ", "").replace("\n", "") == '{"v":1}'
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]
