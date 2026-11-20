"""Tests for Project 5 — Mini Data Engineering Platform.  Run: pytest tests/projects/test_project_05_data_platform.py -v"""
import json
import shutil
from pathlib import Path

import pytest

from labkit.testing import import_project, project_dir

PROJECT = "project_05_data_engineering_pipeline"
registry = import_project(PROJECT, "dataplat.registry")
config_mod = import_project(PROJECT, "dataplat.config")
transforms = import_project(PROJECT, "dataplat.transforms")
sources = import_project(PROJECT, "dataplat.sources")
warehouse_mod = import_project(PROJECT, "dataplat.warehouse")
quality = import_project(PROJECT, "dataplat.quality")
engine_mod = import_project(PROJECT, "dataplat.engine")
cli = import_project(PROJECT, "dataplat.cli")

LAB = Path(__file__).resolve().parents[2]
CTX = lambda tables=None: transforms.StepContext(read_table=lambda name: (tables or {})[name])  # noqa: E731


@pytest.fixture
def platform(tmp_path):
    """A copy of the shipped platform.toml whose outputs go to tmp_path and whose daily data is a private copy."""
    cfg = (project_dir(PROJECT) / "platform.toml").read_text()
    daily = tmp_path / "data" / "daily"
    shutil.copytree(LAB / "datasets/daily", daily)
    for sub in ("csv", "json"):
        shutil.copytree(LAB / "datasets" / sub, tmp_path / "data" / sub)
    cfg = cfg.replace('data_root = "{lab_root}/datasets"', f'data_root = "{(tmp_path / "data").as_posix()}"')
    cfg = cfg.replace('warehouse = "output/warehouse"', f'warehouse = "{(tmp_path / "wh").as_posix()}"')
    cfg = cfg.replace('state_dir = "output/state"', f'state_dir = "{(tmp_path / "state").as_posix()}"')
    path = tmp_path / "platform.toml"
    path.write_text(cfg)
    return path


# ---------------------------------------------------------------- registry & config
def test_registry():
    r = registry.Registry("thing")
    @r.register("a")
    def a():
        return 1
    assert r.get("a") is a and "a" in r and r.names() == ["a"]
    with pytest.raises(ValueError):
        r.register("a")(lambda: 2)
    with pytest.raises(KeyError, match="available"):
        r.get("b")
    assert {"cast", "validate", "dedupe", "lookup", "aggregate", "fill_null"} <= set(registry.TRANSFORMS.names())


def test_load_config_shipped(platform):
    cfg = config_mod.load_config(platform, env={"DATAPLAT_MAX_REJECT_RATIO": "0.05"})
    assert cfg.max_reject_ratio == 0.05 and set(cfg.pipelines) >= {"dim_customer", "fact_orders", "daily_revenue"}
    assert cfg.sources["orders_daily"].options == {"partition_key": "dt"} and cfg.pipelines["fact_orders"].incremental
    order = config_mod.topological_order(cfg.pipelines)
    assert order.index("dim_customer") < order.index("fact_orders") < order.index("daily_revenue")


def test_config_errors(tmp_path):
    p = tmp_path / "bad.toml"
    p.write_text('''
[platform]
name = "x"
data_root = "."
warehouse = "wh"
[sources.s]
type = "parquet"
[pipelines.a]
source = "missing"
steps = [{ op = "explode" }]
sink = { name = "a", mode = "upsert" }
depends_on = ["ghost"]
quality = [{ check = "magic" }]
[pipelines.b]
source_table = "t"
source = "s"
sink = { name = "b", mode = "merge" }
''')
    with pytest.raises(config_mod.ConfigError) as info:
        config_mod.load_config(p, env={})
    text = "\n".join(info.value.problems)
    for fragment in ["unknown type 'parquet'", "unknown source 'missing'", "unknown op 'explode'", "sink.mode", "unknown pipeline 'ghost'",
                     "unknown quality check 'magic'", "exactly one of", "merge sinks need a 'key'"]:
        assert fragment in text


def test_config_cycle(tmp_path):
    p = tmp_path / "cycle.toml"
    p.write_text('[platform]\nname="x"\ndata_root="."\nwarehouse="wh"\n'
                 '[pipelines.a]\nsource_table="b"\ndepends_on=["b"]\nsink={name="a"}\n'
                 '[pipelines.b]\nsource_table="a"\ndepends_on=["a"]\nsink={name="b"}\n')
    with pytest.raises(config_mod.ConfigError, match="cycle"):
        config_mod.load_config(p, env={})


# ---------------------------------------------------------------- transforms
def test_casts_and_validate():
    ctx = CTX()
    rows = [{"q": " 2 ", "t": "2026-01-05T10:00:00+05:30", "d": "15/03/2025", "b": "Yes"}, {"q": "x", "t": "", "d": "", "b": ""}]
    out = transforms.cast(rows, ctx, column="q", to="int")
    assert out == [{**rows[0], "q": 2}] and ctx.rejects[0]["_errors"] == ["q: cannot cast to int"]
    assert transforms.cast(out, ctx, column="t", to="timestamp")[0]["t"] == "2026-01-05T04:30:00Z"
    assert transforms.cast(out, ctx, column="d", to="date")[0]["d"] == "2025-03-15" and transforms.cast(out, ctx, column="b", to="bool")[0]["b"] is True
    ctx2 = CTX()
    v = transforms.validate([{"id": "1", "n": 5, "s": "A"}, {"id": "", "n": 0, "s": "Z", "e": "bad"}, {"id": "3", "n": None, "s": None}], ctx2,
                            rules=[{"column": "id", "check": "required"}, {"column": "n", "check": "min", "value": 1},
                                   {"column": "s", "check": "in", "values": ["A"]}, {"column": "e", "check": "regex", "pattern": r".+@.+"}])
    assert [r["id"] for r in v] == ["1", "3"] and ctx2.rejects[0]["_errors"] == ["id: is required", "n: below min 1", "s: not an allowed value", "e: does not match pattern"]


def test_row_transforms():
    ctx = CTX()
    rows = [{"a": "  x  y ", "b": "Mixed", "n": 2, "p": 2.5, "ts": "2026-01-05T10:00:00Z", "_source": "f"}]
    assert transforms.strip(rows, ctx, columns=["a"])[0]["a"] == "x y" and transforms.upper(rows, ctx, columns=["b"])[0]["b"] == "MIXED"
    assert transforms.strip([{"a": "   "}], ctx, columns=["a"]) == [{"a": None}]
    d = transforms.derive(rows, ctx, column="amt", expr="multiply", args=["n", "p"])
    assert d[0]["amt"] == 5.0 and transforms.derive(d, ctx, column="day", expr="date_of", args=["ts"])[0]["day"] == "2026-01-05"
    assert transforms.select(rows, ctx, columns=["n", "zz"]) == [{"n": 2, "zz": None, "_source": "f"}]
    assert transforms.rename(rows, ctx, mapping={"n": "qty"})[0]["qty"] == 2 and "n" in rows[0]
    assert transforms.fill_null([{"c": None}, {"c": "x"}, {}], ctx, columns=["c"], value="U") == [{"c": "U"}, {"c": "x"}, {"c": "U"}]
    assert len(transforms.filter_rows([{"s": "A"}, {"s": "B"}, {"s": None}], ctx, column="s", operator="not_in", value=["A"])) == 2


def test_dedupe_lookup_aggregate():
    ctx = CTX({"dim": [{"id": "C1", "seg": "smb"}]})
    rows = [{"k": 1, "v": "2026-01-02", "c": "C1", "amt": 10.0}, {"k": 1, "v": "2026-01-03", "c": "C1", "amt": 20.0}, {"k": 2, "v": None, "c": "C9", "amt": 5.0}]
    d = transforms.dedupe(rows, ctx, key=["k"], order_by="v", keep="last")
    assert [r["amt"] for r in d] == [20.0, 5.0] and ctx.stats["duplicates"] == 1
    assert transforms.dedupe(rows, CTX(), key="k", order_by="v", keep="first")[0]["amt"] == 10.0
    lk = transforms.lookup([{**r, "id": r["c"]} for r in d], ctx, table="dim", key="id", columns=["seg"], prefix="c_", default="unknown")
    assert [r["c_seg"] for r in lk] == ["smb", "unknown"]
    strict = CTX({"dim": [{"id": "C1", "seg": "smb"}]})
    assert len(transforms.lookup([{"id": "C9"}], strict, table="dim", key="id", columns=["seg"], require_match=True)) == 0 and strict.rejects
    agg = transforms.aggregate(rows, ctx, group_by=["c"], metrics={"n": {"fn": "count", "column": "k"}, "rev": {"fn": "sum", "column": "amt"},
                                                                  "keys": {"fn": "count_distinct", "column": "k"}, "avg": {"fn": "avg", "column": "amt"}})
    assert agg == [{"c": "C1", "n": 2, "rev": 30.0, "keys": 1, "avg": 15.0}, {"c": "C9", "n": 1, "rev": 5.0, "keys": 1, "avg": 5.0}]


# ---------------------------------------------------------------- sources, warehouse, quality
def test_csv_partitions_incremental(tmp_path):
    root = tmp_path / "daily"
    for d, content in [("2026-01-01", "id\n1\n"), ("2026-01-02", "id\n2\n")]:
        (root / f"dt={d}").mkdir(parents=True)
        (root / f"dt={d}" / "a.csv").write_text(content)
    (root / "dt=2026-01-02" / "copy.csv").write_text("id\n1\n")
    cfg = config_mod.SourceConfig("o", "csv_partitions", root, {"partition_key": "dt"})
    first = sources.csv_partitions_source(cfg)
    assert [r["dt"] for r in first.records] == ["2026-01-01", "2026-01-02"] and first.skipped_files == ["dt=2026-01-02/copy.csv"]
    again = sources.csv_partitions_source(cfg, processed=first.files)
    assert again.records == [] and len(again.skipped_files) == 3
    (root / "dt=2026-01-01" / "a.csv").write_text("id\n1\n9\n")
    changed = sources.csv_partitions_source(cfg, processed=first.files)
    assert [r["id"] for r in changed.records] == ["1", "9"]


def test_warehouse_modes(tmp_path):
    wh = warehouse_mod.Warehouse(tmp_path / "wh")
    with pytest.raises(KeyError):
        wh.read("t")
    wh.write("t", [{"id": "b", "d": "x", "v": "1", "_source": "f"}, {"id": "a", "d": "y", "v": "1"}], mode="overwrite", partition_by="d", key="id")
    assert {r["id"] for r in wh.read("t")} == {"a", "b"} and "_source" not in wh.read("t")[0] and wh.meta("t")["partitions"] == ["x", "y"]
    wh.write("t", [{"id": "b", "d": "x", "v": "2"}, {"id": "c", "d": "x", "v": "1"}, {"id": "a", "d": "y", "v": "0"}], mode="merge", partition_by="d", key="id", version="v")
    by = {r["id"]: r["v"] for r in wh.read("t")}
    assert by == {"a": "1", "b": "2", "c": "1"} and wh.meta("t")["rows"] == 3
    wh.write("t", [{"id": "z", "d": "q", "v": "1"}], mode="overwrite", partition_by="d", key="id")
    assert [r["id"] for r in wh.read("t")] == ["z"] and not [p for p in (tmp_path / "wh").iterdir() if p.name.startswith(".")]
    wh.write("log", [{"x": 1}], mode="append"); wh.write("log", [{"x": 2}], mode="append")
    assert [r["x"] for r in wh.read("log")] == [1, 2] and wh.tables() == ["log", "t"]


def test_quality_checks():
    rows = [{"id": 1, "s": "A", "n": 5}, {"id": 1, "s": "B", "n": -1}, {"id": None, "s": None, "n": None}]
    res = quality.run_checks(rows, [{"check": "unique", "column": "id"}, {"check": "not_null", "column": "id", "severity": "warn"},
                                    {"check": "row_count_min", "value": 3}, {"check": "accepted_values", "column": "s", "values": ["A"]},
                                    {"check": "range", "column": "n", "min": 0}])
    assert [r["passed"] for r in res] == [False, False, True, False, False] and res[1]["severity"] == "warn" and res[0]["column"] == "id"


# ---------------------------------------------------------------- engine end to end
def test_engine_full_and_incremental_runs(platform, tmp_path):
    eng = engine_mod.Engine(config_mod.load_config(platform, env={}))
    r1 = eng.run(run_id="r1")
    assert r1.status == "SUCCEEDED", r1.to_dict()
    fo = r1.pipelines["fact_orders"]
    assert fo["published"] and fo["rows_in"] == fo["rows_out"] + fo["rejected"] + fo["duplicates"] and fo["skipped_files"]
    facts = eng.warehouse.read("fact_orders")
    assert len({f["order_id"] for f in facts}) == len(facts) and all(f["customer_segment"] for f in facts)
    revenue_1 = eng.warehouse.read("daily_revenue")
    r2 = eng.run(run_id="r2")
    assert r2.pipelines["fact_orders"]["status"] == "SKIPPED_NO_NEW_DATA" and eng.warehouse.read("daily_revenue") == revenue_1
    assert len(eng.warehouse.read("_rejects_dim_customer")) == r2.pipelines["dim_customer"]["rejected"]   # overwritten, not accumulated
    new_day = tmp_path / "data" / "daily" / "dt=2026-01-08"
    new_day.mkdir()
    (new_day / "late.csv").write_text("order_id,customer_id,product_id,quantity,unit_price,order_ts,status,updated_at,channel,country\n"
                                      f"{facts[0]['order_id']},{facts[0]['customer_id']},P0001,1,10.0,{facts[0]['order_ts']},DELIVERED,2027-01-01T00:00:00Z,web,IN\n"
                                      "O7777777,C00001,P0001,2,50.0,2026-01-08T10:00:00Z,PLACED,2026-01-08T10:00:00Z,app,IN\n")
    r3 = eng.run(run_id="r3")
    assert r3.pipelines["fact_orders"]["files"] == ["dt=2026-01-08/late.csv"]
    after = {f["order_id"]: f for f in eng.warehouse.read("fact_orders")}
    assert after[facts[0]["order_id"]]["status"] == "DELIVERED" and "O7777777" in after and len(after) == len(facts) + 1
    assert [r["run_id"] for r in eng.state.runs()] == ["r1", "r2", "r3"]


def test_engine_plan_dry_run_and_failures(platform, tmp_path):
    cfg = config_mod.load_config(platform, env={})
    eng = engine_mod.Engine(cfg)
    assert eng.plan(["daily_revenue"]) == ["dim_customer", "dim_product", "fact_orders", "daily_revenue"]
    with pytest.raises(KeyError):
        eng.plan(["nope"])
    dry = eng.run(["dim_product"], dry_run=True)
    assert dry.pipelines["dim_product"]["status"] == "DRY_RUN" and not eng.warehouse.tables() and not (tmp_path / "state" / "runs").exists()
    strict = engine_mod.Engine(config_mod.load_config(platform, env={"DATAPLAT_MAX_REJECT_RATIO": "0.001"}))
    rep = strict.run()
    assert rep.status == "FAILED" and rep.pipelines["dim_customer"]["status"] == "FAILED" and "reject ratio" in rep.pipelines["dim_customer"]["error"]
    assert rep.pipelines["fact_orders"]["status"] == "UPSTREAM_FAILED" and rep.pipelines["daily_revenue"]["status"] == "UPSTREAM_FAILED"
    assert rep.pipelines["dim_product"]["status"] == "SUCCEEDED"


def test_quality_gate_blocks_publish(platform):
    text = platform.read_text().replace('{ check = "row_count_min", value = 900 }', '{ check = "row_count_min", value = 999999 }')
    platform.write_text(text)
    eng = engine_mod.Engine(config_mod.load_config(platform, env={}))
    rep = eng.run(["dim_customer"])
    assert rep.pipelines["dim_customer"]["status"] == "FAILED" and not eng.warehouse.exists("dim_customer")


def test_cli(platform, capsys):
    base = ["--config", str(platform), "--log-level", "ERROR"]
    assert cli.main(base + ["validate-config"]) == 0 and "plan:" in capsys.readouterr().out
    assert cli.main(base + ["plan", "--pipeline", "fact_orders"]) == 0 and capsys.readouterr().out.split() == ["dim_customer", "dim_product", "fact_orders"]
    assert cli.main(base + ["run", "--run-id", "cli-1"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "SUCCEEDED"
    assert cli.main(base + ["show", "dim_product", "--limit", "2"]) == 0 and len(capsys.readouterr().out.splitlines()) == 2
    assert cli.main(base + ["status"]) == 0 and json.loads(capsys.readouterr().out)["tables"]["dim_product"] == 200
    assert cli.main(base + ["show", "missing_table"]) == 1
    assert cli.main(["--config", str(platform.parent / "missing.toml"), "validate-config"]) == 2
