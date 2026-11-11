"""Checks on the built warehouse: every planted problem is caught, and the governed metrics hold up."""
import json
from pathlib import Path

import duckdb
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def con():
    db = ROOT / "warehouse.duckdb"
    if not db.exists():
        pytest.skip("run `python generator/generate.py && dbt build --profiles-dir .` first")
    return duckdb.connect(str(db), read_only=True)


def one(con, sql):
    return con.execute(sql).fetchone()[0]


def test_duplicate_snapshot_load_is_flagged(con):
    rows = con.execute("select snapshot_date::varchar, location_id, rows_loaded, skus from audit_snapshot_duplicates").fetchall()
    assert rows == [("2026-05-12", "DC1", 480, 240)]


def test_reconciliation_is_clean_after_deduplication(con):
    assert one(con, "select count(*) from recon_events_vs_snapshots") == 0


def test_reconciliation_would_catch_the_double_load_without_it(con):
    bad = con.execute("""with s as (select snapshot_date::date d, location_id, sku, sum(on_hand::int) oh
          from read_csv('data/raw/inventory_snapshots.csv', header = true, all_varchar = true) group by all),
        snap as (select d, location_id, sku, oh - lag(oh) over (partition by location_id, sku order by d) ch from s),
        ev as (select event_date d, location_id, sku, sum(quantity) e from stg_inventory_events group by all)
        select s.d::varchar, count(*) from snap s left join ev using (d, location_id, sku)
        where ch is not null and ch <> coalesce(e, 0) group by 1 order by 1""").fetchall()
    assert bad == [("2026-05-12", 240), ("2026-05-13", 240)]


def test_stream_duplicates_are_removed(con):
    raw = sum(1 for _ in open(ROOT / "data" / "raw" / "inventory_events.jsonl"))
    assert one(con, "select count(*) from stg_inventory_events") < raw
    assert one(con, "select count(*) - count(distinct event_id) from stg_inventory_events") == 0


def test_problem_vendors_stand_out(con):
    v = {r[0]: r[1:] for r in con.execute("select vendor_id, otif_rate, fill_rate, asn_mismatch_rate from mart_vendor_scorecard").fetchall()}
    assert v["V07"][0] < 0.1 and v["V07"][1] < 0.9                     # late and short
    assert v["V11"][2] > 0.3 and all(x[2] < 0.1 for k, x in v.items() if k != "V11")  # ASN mismatch


def test_v07_shows_up_at_the_dc_first(con):
    worst = one(con, "select vendor_id from mart_instock_by_vendor order by dc_instock_rate limit 1")
    assert worst == "V07"


def test_every_governed_metric_compiles_to_a_number(con):
    for m in yaml.safe_load((ROOT / "semantic" / "metrics.yml").read_text())["metrics"]:
        v = one(con, f"select {m['expression']} from {m['model']}")
        assert v is not None and v > 0, m["name"]


def test_weeks_of_supply_counts_sales_once(con):
    m = next(x for x in yaml.safe_load((ROOT / "semantic" / "metrics.yml").read_text())["metrics"] if x["name"] == "weeks_of_supply")
    governed = one(con, f"select {m['expression']} from {m['model']}")
    direct = one(con, """select sum(on_hand) / (select sum(weekly_units) from (select distinct category, weekly_units from mart_weeks_of_supply))
                         from mart_weeks_of_supply""")
    assert governed == pytest.approx(direct)
