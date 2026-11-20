"""Tests for 05_functions_and_oop/04_classes_inheritance_composition.ipynb

Run: pytest tests/functions_oop/test_05_04_classes_inheritance_composition.py -v
"""
import pytest

from labkit.testing import load

nb = load("05_functions_and_oop/04_classes_inheritance_composition.ipynb")


def test_batch():
    src = [{"i": 1}, {"i": 2}, {"i": 3}]
    b = nb.Batch(src, "b7")
    src.append({"i": 4})
    assert len(b) == 3 and [r["i"] for r in b] == [1, 2, 3] and b[0] == {"i": 1} and b[-1] == {"i": 3}
    s = b[1:]
    assert isinstance(s, nb.Batch) and len(s) == 2 and s.batch_id == "b7"
    assert not nb.Batch() and b and repr(b) == "Batch(id='b7', size=3)"
    b.append({"i": 9})
    assert len(b) == 4 and nb.Batch([1], "x") == nb.Batch([1], "x") and nb.Batch([1], "x") != nb.Batch([1], "y")


def test_csv_source(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text('id,name\n1,"Kalyan, B"\n\n2\n3,Diya\n', encoding="utf-8")
    src = nb.CsvSource(p)
    assert list(src.records()) == [{"id": "1", "name": "Kalyan, B"}, {"id": "3", "name": "Diya"}] and src.skipped == 1
    assert len(list(src.records())) == 2

def test_pipe_delimiter(tmp_path):
    p = tmp_path / "a.txt"; p.write_text("a|b\n1|2\n")
    assert list(nb.CsvSource(p, delimiter="|").records()) == [{"a": "1", "b": "2"}]

def test_jsonl_source(tmp_path):
    p = tmp_path / "a.jsonl"; p.write_text('{"a": 1}\nnot json\n[1]\n{"a": 2}\n')
    src = nb.JsonlSource(p)
    assert list(src.records()) == [{"a": 1}, {"a": 2}] and src.skipped == 2 and isinstance(src, nb.FileSource)

def test_base_is_abstract_ish(tmp_path):
    p = tmp_path / "x"; p.write_text("x\n")
    FileSource = nb.FileSource          # bind first: a missing class must skip, not satisfy pytest.raises
    with pytest.raises(NotImplementedError):
        list(FileSource(p).records())


def strip_names(rs):
    return ({**r, "name": r["name"].strip()} for r in rs)

def only_active(rs):
    return (r for r in rs if r["active"])

def test_pipeline_run_and_chain():
    p = nb.Pipeline(name="clean").add(strip_names).add(only_active)
    assert p.run([{"name": " a ", "active": True}, {"name": "b", "active": False}]) == [{"name": "a", "active": True}]
    assert len(p) == 2 and repr(p) == "Pipeline('clean', steps=2)"

def test_pipeline_operators():
    p1, p2 = nb.Pipeline(strip_names, name="p1"), nb.Pipeline(only_active, name="p2")
    p3 = p1 | p2
    assert p3.name == "p1+p2" and len(p3) == 2 and len(p1) == 1
    p4 = p3 | (lambda rs: sorted(rs, key=lambda r: r["name"]))
    assert p4.run([{"name": "z", "active": True}, {"name": " y", "active": True}]) == [{"name": "y", "active": True}, {"name": "z", "active": True}]
    assert nb.Pipeline().run([1, 2]) == [1, 2]


def test_registry_and_create():
    assert {"rename", "cast", "drop"} <= set(nb.Transform.registry)
    t = nb.Transform.create("rename", mapping={"amt": "amount"})
    assert t({"amt": 1, "x": 2}) == {"amount": 1, "x": 2}
    with pytest.raises(KeyError, match="known"):
        nb.Transform.create("explode")

def test_duplicate_and_abstract_helper():
    with pytest.raises(ValueError):
        class Again(nb.Transform):
            name = "rename"
    class Helper(nb.Transform):
        pass
    assert "Helper" not in nb.Transform.registry and None not in nb.Transform.registry

def test_run_transforms():
    specs = [{"name": "rename", "mapping": {"Qty": "quantity"}}, {"name": "cast", "column": "quantity", "to": "int"},
             {"name": "drop", "columns": ["junk"]}]
    assert nb.run_transforms({"Qty": "3", "junk": 1, "id": "A"}, specs) == {"quantity": 3, "id": "A"}
    assert nb.run_transforms({"quantity": None}, [{"name": "cast", "column": "quantity", "to": "float"}]) == {"quantity": None}


ROWS = [{"id": 1, "country": "IN", "amount": 10.0}, {"id": 2, "country": "FI", "amount": 5.0},
        {"id": 3, "country": "IN", "amount": None}, {"id": 4, "country": "IN", "amount": 7.5}]

def test_table_basics_and_immutability():
    t = nb.Table(ROWS)
    assert len(t) == 4 and t.columns == ["id", "country", "amount"] and t["id"] == [1, 2, 3, 4]
    for row in t:
        row["id"] = 99
    assert t["id"] == [1, 2, 3, 4]
    w = t.where(lambda r: r["country"] == "IN")
    assert len(w) == 3 and len(t) == 4
    assert t.select("id").columns == ["id"] and t.order_by("amount", desc=True)["id"] == [1, 4, 2, 3]
    assert t.with_column("double", lambda r: (r["amount"] or 0) * 2)["double"] == [20.0, 10.0, 0, 15.0]

def test_table_group_by_agg():
    g = nb.Table(ROWS).group_by("country").agg(total=("amount", lambda xs: sum(x for x in xs if x is not None)), n=("id", len))
    assert list(g) == [{"country": "IN", "total": 17.5, "n": 3}, {"country": "FI", "total": 5.0, "n": 1}]

def test_table_join():
    people = nb.Table([{"country": "IN", "name": "India"}, {"country": "FI", "name": "Finland"}, {"country": "FI", "name": "Suomi"}])
    j = nb.Table(ROWS).join(people, on="country")
    assert len(j) == 5 and j.columns == ["id", "country", "amount", "name"]
    left = nb.Table([{"country": "SE"}]).join(people, on="country", how="left")
    assert list(left) == [{"country": "SE", "name": None}]
    assert len(nb.Table([{"country": "SE"}]).join(people, on="country")) == 0
    with pytest.raises(ValueError):
        nb.Table().join(people, on="x", how="outer")

def test_table_repr():
    text = repr(nb.Table(ROWS))
    assert text.splitlines()[0].split() == ["id", "country", "amount"] and text.endswith("[4 rows x 3 columns]")
