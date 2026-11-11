"""Exports the certified marts, dbt test results, lineage and metric catalog to site/data.json."""
import json
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    c = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    rows = lambda sql: [dict(zip([d[0] for d in c.description], r)) for r in c.execute(sql).fetchall()]
    metrics = yaml.safe_load((ROOT / "semantic" / "metrics.yml").read_text())["metrics"]
    certified = {m["name"]: c.execute(f"select {m['expression']} from {m['model']}").fetchone()[0] for m in metrics}

    rr = json.loads((ROOT / "target" / "run_results.json").read_text())
    manifest = json.loads((ROOT / "target" / "manifest.json").read_text())
    tests = [{"name": r["unique_id"].split(".")[2], "status": r["status"], "failures": r.get("failures") or 0}
             for r in rr["results"] if r["unique_id"].startswith("test.")]
    nodes = {k: v for k, v in manifest["nodes"].items() if v["resource_type"] == "model"}
    lineage = [{"name": v["name"], "layer": v["fqn"][1] if len(v["fqn"]) > 2 else "other",
                "depends_on": [manifest["nodes"][d]["name"] for d in v["depends_on"]["nodes"] if d in nodes]} for v in nodes.values()]

    def r4(x): return round(float(x), 4) if x is not None else None
    data = {
        "certified": {k: r4(v) for k, v in certified.items()},
        "metrics": [{k: m[k] for k in ("name", "label", "model", "expression", "format", "grain", "owner", "definition")} for m in metrics],
        "vendors": [{k: (r4(v) if isinstance(v, float) else v) for k, v in r.items()} for r in rows(
            "select s.*, i.dc_instock_rate, i.instock_rate from mart_vendor_scorecard s join mart_instock_by_vendor i using (vendor_id, vendor_name) order by otif_rate")],
        "instock_weekly": [{"w": str(r["week_start"]), "region": r["region"], "category": r["category"], "v": r4(r["instock_rate"])}
                           for r in rows("select * from mart_instock_weekly")],
        "wos": [{k: (r4(v) if isinstance(v, float) else v) for k, v in r.items()} for r in rows("select category, location_type, on_hand, weekly_units, weeks_of_supply from mart_weeks_of_supply")],
        "sell_through": [{"w": str(r["week_start"]), "category": r["category"], "v": r4(r["sell_through"]), "sold": int(r["units_sold"]), "end": int(r["ending_on_hand"])}
                         for r in rows("select * from mart_sell_through_weekly")],
        "tests": tests, "lineage": lineage,
        "incident": {"duplicates": rows("select snapshot_date::varchar as date, location_id, rows_loaded, skus from audit_snapshot_duplicates"),
                     "events_total": c.execute("select count(*) from stg_inventory_events").fetchone()[0],
                     "events_raw": sum(1 for _ in open(ROOT / "data" / "raw" / "inventory_events.jsonl")),
                     "recon_without_dedupe": rows("""with s as (select snapshot_date::date d, location_id, sku, sum(on_hand::int) oh
                         from read_csv('data/raw/inventory_snapshots.csv', header = true, all_varchar = true) group by all),
                         snap as (select d, location_id, sku, oh - lag(oh) over (partition by location_id, sku order by d) ch from s),
                         ev as (select event_date d, location_id, sku, sum(quantity) e from stg_inventory_events group by all)
                         select s.d::varchar as date, count(*) as mismatches from snap s left join ev using (d, location_id, sku)
                         where ch is not null and ch <> coalesce(e, 0) group by 1 order by 1"""),
                     "recon_with_dedupe": c.execute("select count(*) from recon_events_vs_snapshots").fetchone()[0],
                     "late_share": r4(c.execute("select avg((ingestion_lag_hours >= 6)::int) from stg_inventory_events").fetchone()[0])},
        "counts": {t: c.execute(f"select count(*) from {t}").fetchone()[0] for t in ("fct_po_lines", "fct_inventory_daily", "fct_sales_daily", "fct_store_shipments")},
    }
    (ROOT / "site" / "data.json").write_text(json.dumps(data, separators=(",", ":"), default=str))
    print(f"site/data.json: {(ROOT / 'site' / 'data.json').stat().st_size:,} bytes")
    print({k: data["certified"][k] for k in data["certified"]}, [v for v in data["vendors"] if v["vendor_id"] == "V11"])


if __name__ == "__main__":
    main()
