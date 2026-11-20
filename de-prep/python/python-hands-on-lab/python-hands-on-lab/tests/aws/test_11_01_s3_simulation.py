"""Tests for 11_python_for_aws/01_s3_simulation.ipynb

Run: pytest tests/aws/test_11_01_s3_simulation.py -v
"""
import pytest

from labkit.testing import load

nb = load("11_python_for_aws/01_s3_simulation.ipynb")


def test_s3_to_local(tmp_path):
    assert nb.s3_to_local("s3://b/a/x.csv", tmp_path) == tmp_path / "b" / "a" / "x.csv"
    assert nb.s3_to_local("s3://b/prefix/", tmp_path) == tmp_path / "b" / "prefix" and nb.s3_to_local("s3://b", tmp_path) == tmp_path / "b"
    for bad in ["https://b/x", "s3:///x", "s3://b/../../etc/passwd", "s3://b/a/../../x"]:
        with pytest.raises(ValueError):
            nb.s3_to_local(bad, tmp_path)


import shutil
from pathlib import Path

def fresh_s3(tmp_path):
    root = tmp_path / "s3"
    shutil.copytree(Path(__file__).resolve().parents[2] / "datasets/s3", root)
    return root

def test_list_prefix(tmp_path):
    root = fresh_s3(tmp_path)
    flat = nb.list_prefix(root, "lab-raw-bucket", "sales/")
    assert len(flat["Contents"]) == 6 and flat["CommonPrefixes"] == [] and flat["Contents"][0]["Key"] == "sales/ingest_date=2026-01-10/part-00000.csv"
    rolled = nb.list_prefix(root, "lab-raw-bucket", "sales/", delimiter="/")
    assert rolled["Contents"] == [] and [p["Prefix"] for p in rolled["CommonPrefixes"]] == [f"sales/ingest_date=2026-01-1{i}/" for i in range(3)]
    top = nb.list_prefix(root, "lab-raw-bucket", delimiter="/")
    assert [p["Prefix"] for p in top["CommonPrefixes"]] == ["customers/", "sales/"]
    assert nb.list_prefix(root, "lab-processed-bucket")["Contents"][0]["Key"] == ".keep"
    with pytest.raises(FileNotFoundError):
        nb.list_prefix(root, "nope")


import shutil
from pathlib import Path

def fresh_s3(tmp_path):
    root = tmp_path / "s3"
    shutil.copytree(Path(__file__).resolve().parents[2] / "datasets/s3", root)
    return root

def test_move_prefix(tmp_path):
    root = fresh_s3(tmp_path)
    n = nb.move_prefix(root, "s3://lab-raw-bucket/sales/", "s3://lab-processed-bucket/archive/sales/")
    assert n == 6 and not (root / "lab-raw-bucket" / "sales").exists()
    assert len(list((root / "lab-processed-bucket" / "archive" / "sales").rglob("*.csv"))) == 6
    assert nb.move_prefix(root, "s3://lab-raw-bucket/customers/", "s3://lab-raw-bucket/customers_copy/", delete_source=False) == 1
    assert (root / "lab-raw-bucket" / "customers" / "customers.json").exists()
    with pytest.raises(ValueError):
        nb.move_prefix(root, "s3://lab-raw-bucket/customers/", "s3://lab-raw-bucket/customers/backup/")


import shutil
from pathlib import Path

def fresh_s3(tmp_path):
    root = tmp_path / "s3"
    shutil.copytree(Path(__file__).resolve().parents[2] / "datasets/s3", root)
    return root

def test_local_s3_client_crud(tmp_path):
    s3 = nb.LocalS3Client(fresh_s3(tmp_path))
    s3.create_bucket(Bucket="scratch")
    etag = s3.put_object(Bucket="scratch", Key="a/b.txt", Body="hello")["ETag"]
    import hashlib
    assert etag == f'"{hashlib.md5(b"hello").hexdigest()}"'
    obj = s3.get_object(Bucket="scratch", Key="a/b.txt")
    assert obj["Body"].read() == b"hello" and obj["ContentLength"] == 5 and s3.head_object(Bucket="scratch", Key="a/b.txt")["ETag"] == etag
    assert s3.delete_object(Bucket="scratch", Key="a/b.txt") == {} and s3.delete_object(Bucket="scratch", Key="a/b.txt") == {}
    with pytest.raises(nb.ClientError) as info:
        s3.get_object(Bucket="scratch", Key="a/b.txt")
    assert info.value.response["Error"]["Code"] == "NoSuchKey"
    with pytest.raises(nb.ClientError) as info:
        s3.put_object(Bucket="missing", Key="x", Body=b"")
    assert info.value.response["Error"]["Code"] == "NoSuchBucket"

def test_local_s3_client_pagination(tmp_path):
    s3 = nb.LocalS3Client(fresh_s3(tmp_path))
    keys, token = [], None
    while True:
        kwargs = {"Bucket": "lab-raw-bucket", "Prefix": "sales/", "MaxKeys": 4}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        keys += [o["Key"] for o in resp.get("Contents", [])]
        if not resp["IsTruncated"]:
            break
        token = resp["NextContinuationToken"]
    assert len(keys) == 6 and keys == sorted(keys)
    assert "Contents" not in s3.list_objects_v2(Bucket="lab-raw-bucket", Prefix="nothing/") and s3.list_objects_v2(Bucket="lab-raw-bucket", Prefix="nothing/")["KeyCount"] == 0


import shutil
from pathlib import Path

def fresh_s3(tmp_path):
    root = tmp_path / "s3"
    shutil.copytree(Path(__file__).resolve().parents[2] / "datasets/s3", root)
    return root

def _event(*keys, name="ObjectCreated:Put", bucket="lab-raw-bucket"):
    from urllib.parse import quote_plus
    return {"Records": [{"eventName": name, "s3": {"bucket": {"name": bucket}, "object": {"key": quote_plus(k, safe="/")}}} for k in keys]}

def test_handle_s3_event(tmp_path):
    root = fresh_s3(tmp_path)
    keys = ["sales/ingest_date=2026-01-10/part-00000.csv", "sales/ingest_date=2026-01-11/part-00001.csv"]
    ev = _event(*keys)
    ev["Records"].append(_event("customers/customers.json")["Records"][0])
    ev["Records"].append(_event(keys[0], name="ObjectRemoved:Delete")["Records"][0])
    ev["Records"].append(_event("sales/missing file.csv")["Records"][0])
    r = nb.handle_s3_event(ev, root)
    assert r["processed"] == keys and r["skipped"] == [] and r["ignored"] == 2 and r["errors"][0]["key"] == "sales/missing file.csv"
    clean = root / "lab-processed-bucket/clean/sales/ingest_date=2026-01-10/part-00000.jsonl"
    assert clean.exists() and r["valid_rows"] > 50 and r["valid_rows"] + r["rejected_rows"] > 100
    again = nb.handle_s3_event(_event(*keys), root)
    assert again["processed"] == [] and again["skipped"] == keys
    p = root / "lab-raw-bucket" / keys[0]
    p.write_text(p.read_text() + "O1,C00001,P0001,1,10,2026-01-10T00:00:00Z,PLACED,2026-01-10T00:00:00Z,web,IN\n")
    assert nb.handle_s3_event(_event(keys[0]), root)["processed"] == [keys[0]]
