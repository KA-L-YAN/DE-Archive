"""Tests for 11_python_for_aws/02_glue_style_jobs.ipynb

Run: pytest tests/aws/test_11_02_glue_style_jobs.py -v
"""
import pytest

from labkit.testing import load

nb = load("11_python_for_aws/02_glue_style_jobs.ipynb")


def test_get_resolved_options():
    argv = ["script.py", "--JOB_NAME", "daily_sales", "--TempDir", "s3://tmp", "--input_path=s3://raw/sales/", "--job-bookmark-option", "job-bookmark-enable", "--JOB_NAME", "final"]
    assert nb.get_resolved_options(argv, ["JOB_NAME", "input_path"]) == {"JOB_NAME": "final", "input_path": "s3://raw/sales/"}
    with pytest.raises(ValueError, match="output_path.*env"):
        nb.get_resolved_options(argv, ["output_path", "JOB_NAME", "env"])


def test_build_parser_ok():
    from datetime import date
    args, unknown = nb.build_parser().parse_known_args(["--config", "s3://cfg/job.json", "--ingest-date", "2026-01-10", "--dry-run", "--log-level", "debug", "--TempDir", "x"])
    assert (args.config, args.ingest_date, args.env, args.batch_size, args.dry_run, args.log_level) == ("s3://cfg/job.json", date(2026, 1, 10), "dev", 500, True, "DEBUG")
    assert unknown == ["--TempDir", "x"]

@pytest.mark.parametrize("argv", [[], ["--config", "/local/path.json"], ["--config", "s3://c/j.json", "--ingest-date", "10-01-2026"],
                                  ["--config", "s3://c/j.json", "--batch-size", "0"], ["--config", "s3://c/j.json", "--env", "staging"]])
def test_build_parser_errors(argv, capsys):
    with pytest.raises(SystemExit):
        nb.build_parser().parse_args(argv)


def test_emf_record():
    r = nb.emf_record("Lab/ETL", {"RowsRead": (1000, "Count"), "Duration": (12.5, "Seconds")}, {"JobName": "daily_sales", "Env": "dev"}, 1767600000000)
    assert r == {"_aws": {"Timestamp": 1767600000000, "CloudWatchMetrics": [{"Namespace": "Lab/ETL", "Dimensions": [["JobName", "Env"]],
                 "Metrics": [{"Name": "RowsRead", "Unit": "Count"}, {"Name": "Duration", "Unit": "Seconds"}]}]},
                 "JobName": "daily_sales", "Env": "dev", "RowsRead": 1000, "Duration": 12.5}
    import json
    json.dumps(r)
    with pytest.raises(ValueError):
        nb.emf_record("x", {"A": (1, "Furlongs")}, {}, 0)
    with pytest.raises(ValueError):
        nb.emf_record("x", {"Env": (1, "Count")}, {"Env": "dev"}, 0)


import shutil
from pathlib import Path

def fresh_s3(tmp_path):
    root = tmp_path / "s3"
    shutil.copytree(Path(__file__).resolve().parents[2] / "datasets/s3", root)
    return root

def test_job_bookmark(tmp_path):
    root = fresh_s3(tmp_path)
    objs = [{"Key": "sales/a.csv", "ETag": '"1"'}, {"Key": "sales/b.csv", "ETag": '"2"'}]
    bm = nb.JobBookmark(root, "daily_sales")
    assert bm.filter_new("raw", objs) == objs
    bm.mark("raw", objs[:1])
    assert nb.JobBookmark(root, "daily_sales").filter_new("raw", objs) == objs
    bm.commit()
    bm2 = nb.JobBookmark(root, "daily_sales")
    assert bm2.filter_new("raw", objs) == objs[1:] and bm2.runs == 1
    changed = [{"Key": "sales/a.csv", "ETag": '"1b"'}]
    assert bm2.filter_new("raw", changed) == changed and bm2.filter_new("other-bucket", objs[:1]) == objs[:1]
    bm2.reset()
    assert nb.JobBookmark(root, "daily_sales").filter_new("raw", objs) == objs and not (root / "lab-processed-bucket/_bookmarks/daily_sales.json").exists()


import shutil
from pathlib import Path

def fresh_s3(tmp_path):
    root = tmp_path / "s3"
    shutil.copytree(Path(__file__).resolve().parents[2] / "datasets/s3", root)
    return root

ARGV = ["job.py", "--JOB_NAME", "daily_sales", "--config_uri", "s3://lab-config-bucket/jobs/daily_sales.json"]

def test_run_sales_job_bookmarked(tmp_path):
    root = fresh_s3(tmp_path)
    s1 = nb.run_sales_job(ARGV, root, now_ms=1)
    assert sorted(s1["partitions"]) == ["2026-01-10", "2026-01-11", "2026-01-12"] and s1["status"] == "SUCCEEDED"
    for p in s1["partitions"].values():
        assert p["read"] == p["valid"] + p["rejected"] + p["duplicates"]
    out = root / "lab-processed-bucket/sales_daily/ingest_date=2026-01-10/part-00000.jsonl"
    assert out.exists() and len(out.read_text().splitlines()) == s1["partitions"]["2026-01-10"]["valid"]
    assert s1["metrics"]["RowsRead"] == sum(p["read"] for p in s1["partitions"].values()) and (root / "lab-processed-bucket/sales_daily/_runs/daily_sales-1.json").exists()
    s2 = nb.run_sales_job(ARGV, root, now_ms=2)
    assert s2["partitions"] == {} and s2["metrics"]["RowsRead"] == 0
    f = root / "lab-raw-bucket/sales/ingest_date=2026-01-11/part-00000.csv"
    f.write_text(f.read_text() + "O9999999,C00001,P0001,2,10.0,2026-01-11T09:00:00Z,placed,2026-01-11T09:00:00Z,web,IN\n")
    s3 = nb.run_sales_job(ARGV, root, now_ms=3)
    assert list(s3["partitions"]) == ["2026-01-11"] and s3["partitions"]["2026-01-11"]["valid"] == s1["partitions"]["2026-01-11"]["valid"] + 1

def test_run_sales_job_explicit_partition_and_args(tmp_path):
    root = fresh_s3(tmp_path)
    s = nb.run_sales_job(ARGV + ["--ingest_date", "2026-01-12"], root, now_ms=5)
    assert list(s["partitions"]) == ["2026-01-12"]
    again = nb.run_sales_job(ARGV + ["--ingest_date", "2026-01-12"], root, now_ms=6)
    assert again["partitions"] == s["partitions"]
    with pytest.raises(ValueError):
        nb.run_sales_job(["job.py", "--JOB_NAME", "x"], root)
