"""
Source-system extracts for a fictional sporting goods retailer, Ridgeline Outfitters:
2 distribution centers, 40 stores, 240 SKUs from 12 vendors, 26 weeks (Feb–Jul 2026).

The files mirror what a warehouse management system (like Manhattan) and a
merchandising system hand to an analytics team:

  purchase_orders.csv     PO lines: vendor, SKU, DC, quantity, cost, promised date
  asn.csv                 advance ship notices from vendors (what they say they sent)
  dc_receipts.csv         what the DC actually received, and when
  store_shipments.csv     DC-to-store replenishment shipments
  pos_sales.csv           daily store sales by SKU
  inventory_snapshots.csv end-of-day on-hand by location and SKU (the WMS snapshot feed)
  inventory_events.jsonl  the movement event stream (receipts, shipments, sales, adjustments)
                          with the problems streams really have: duplicates, late and
                          out-of-order events

Planted problems, listed in data/raw/known_issues.json, so the tests can prove they're caught:
  - the snapshot feed for DC1 was loaded twice on 2026-05-12 (doubled on-hand)
  - vendor V07 short-ships and runs late; vendor V11 sends ASNs that don't match receipts
  - 1.5% of events are duplicated, 2% arrive late, some out of order
"""
import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "raw"
START, WEEKS = date(2026, 2, 1), 26
DAYS = [START + timedelta(d) for d in range(WEEKS * 7)]
DCS = ["DC1", "DC2"]
STORES = [f"S{n:03d}" for n in range(101, 141)]
CATS = {"Footwear": (54, 0.52), "Apparel": (24, 0.55), "Outdoors": (38, 0.60), "Team Sports": (31, 0.58), "Fitness": (45, 0.62)}
rng = random.Random(21)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    vendors = [{"vendor_id": f"V{v:02d}", "vendor_name": n, "lead_time_days": lt} for v, (n, lt) in enumerate([
        ("Summit Gear", 14), ("Trailhead Supply", 21), ("Court & Field", 18), ("Stride Footwear", 28), ("Peak Apparel", 24),
        ("Iron Works Fitness", 30), ("Blue Line Sports", 20), ("Northwind Outdoor", 25), ("Velocity Run", 26),
        ("Granite Packs", 22), ("Coastal Paddle", 19), ("Ember Camp", 23)], start=1)]
    skus, n = [], 0
    for cat, (price, cost_ratio) in CATS.items():
        for i in range(48):
            n += 1
            p = round(price * rng.uniform(0.6, 1.6), 2)
            skus.append({"sku": f"SKU{n:04d}", "category": cat, "description": f"{cat} item {i + 1}",
                         "vendor_id": rng.choice(vendors)["vendor_id"], "unit_cost": round(p * cost_ratio, 2), "retail_price": p})
    locations = [{"location_id": d, "location_type": "DC", "region": "East" if d == "DC1" else "Central"} for d in DCS] + \
                [{"location_id": s, "location_type": "Store", "region": "East" if int(s[1:]) < 121 else "Central"} for s in STORES]
    dc_for = {s: "DC1" if int(s[1:]) < 121 else "DC2" for s in STORES}

    velocity = {s["sku"]: rng.lognormvariate(-0.6, 0.8) for s in skus}
    store_size = {s: rng.uniform(0.7, 1.4) for s in STORES}
    on_hand = {(l, s["sku"]): 0 for l in DCS + STORES for s in skus}
    for s in skus:
        for st in STORES:
            # stores open at their replenishment target, so week one isn't an artificial stockout
            on_hand[(st, s["sku"])] = max(4, round(velocity[s["sku"]] * store_size[st] * 4)) + rng.randint(0, 2)
        lt = next(x for x in vendors if x["vendor_id"] == s["vendor_id"])["lead_time_days"]
        weekly_dc = velocity[s["sku"]] * 20 * 0.35 * 7 * 1.2
        for dc in DCS:
            # DCs open with enough to cover the vendor lead time plus three weeks, like a real network
            on_hand[(dc, s["sku"])] = round(weekly_dc * (lt / 7 + 3)) + rng.randint(5, 20)
    pos, asn, receipts, ships, sales, snaps, events = [], [], [], [], [], [], []
    po_n, eid = 0, 0
    pending = []          # receipts scheduled to land
    issues = []

    def event(ts, loc, sku, typ, qty):
        nonlocal eid
        eid += 1
        e = {"event_id": f"E{eid:08d}", "event_ts": ts.isoformat(timespec="seconds"), "location_id": loc, "sku": sku,
             "event_type": typ, "quantity": qty}
        lag = timedelta(minutes=rng.randint(1, 30))
        if rng.random() < 0.02:
            lag = timedelta(hours=rng.randint(6, 60))          # late arrival
        e["ingested_ts"] = (ts + lag).isoformat(timespec="seconds")
        events.append(e)
        if rng.random() < 0.015:                               # duplicate delivery
            events.append({**e, "ingested_ts": (ts + lag + timedelta(minutes=rng.randint(1, 90))).isoformat(timespec="seconds")})

    for day in DAYS:
        wk = (day - START).days // 7
        season = 1 + 0.35 * (day.month in (5, 6, 7)) + 0.25 * (day.weekday() >= 5)
        # sales
        for st in STORES:
            for s in skus:
                lam = velocity[s["sku"]] * store_size[st] * season * 0.35
                q = min(on_hand[(st, s["sku"])], sum(1 for _ in range(6) if rng.random() < lam / 6))
                if q:
                    on_hand[(st, s["sku"])] -= q
                    sales.append({"sale_date": day.isoformat(), "store_id": st, "sku": s["sku"], "units": q,
                                  "net_sales": round(q * s["retail_price"] * rng.uniform(0.85, 1.0), 2)})
                    event(datetime.combine(day, datetime.min.time()) + timedelta(hours=rng.randint(10, 20)), st, s["sku"], "SALE", -q)
        # receipts landing today
        for r in [p for p in pending if p["receipt_date"] == day]:
            on_hand[(r["dc_id"], r["sku"])] += r["received_qty"]
            receipts.append({k: (v.isoformat() if isinstance(v, date) else v) for k, v in r.items()})
            event(datetime.combine(day, datetime.min.time()) + timedelta(hours=7), r["dc_id"], r["sku"], "RECEIPT", r["received_qty"])
        pending = [p for p in pending if p["receipt_date"] != day]
        # store replenishment twice a week
        if day.weekday() in (0, 3):
            for st in STORES:
                dc = dc_for[st]
                for s in skus:
                    target = max(4, round(velocity[s["sku"]] * store_size[st] * 4))
                    need = target - on_hand[(st, s["sku"])]
                    if need > 0 and on_hand[(dc, s["sku"])] > 0:
                        q = min(need, on_hand[(dc, s["sku"])])
                        on_hand[(dc, s["sku"])] -= q
                        on_hand[(st, s["sku"])] += q
                        ships.append({"ship_date": day.isoformat(), "from_dc": dc, "store_id": st, "sku": s["sku"], "units": q})
                        t = datetime.combine(day, datetime.min.time()) + timedelta(hours=5)
                        event(t, dc, s["sku"], "SHIP_OUT", -q)
                        event(t + timedelta(hours=8), st, s["sku"], "STORE_RECEIPT", q)
        # weekly purchase orders on Mondays
        if day.weekday() == 0 and wk < WEEKS - 3:
            for dc in DCS:
                for s in skus:
                    v = next(x for x in vendors if x["vendor_id"] == s["vendor_id"])
                    weekly = velocity[s["sku"]] * 20 * 0.35 * 7 * 1.2
                    if on_hand[(dc, s["sku"])] < weekly * (v["lead_time_days"] / 7 + 2):
                        po_n += 1
                        qty = max(12, round(weekly * 4 / 6) * 6)
                        promised = day + timedelta(v["lead_time_days"])
                        po = f"PO{po_n:06d}"
                        pos.append({"po_number": po, "po_line": 1, "vendor_id": v["vendor_id"], "sku": s["sku"], "dc_id": dc,
                                    "order_date": day.isoformat(), "promised_date": promised.isoformat(), "ordered_qty": qty,
                                    "unit_cost": s["unit_cost"]})
                        late = rng.choice([0] * 8 + [1, 2]) if v["vendor_id"] != "V07" else rng.choice([3, 5, 7, 9])
                        short = 1.0 if v["vendor_id"] != "V07" else rng.choice([0.7, 0.8, 0.9, 1.0])
                        if rng.random() < 0.04:
                            short = rng.choice([0.9, 0.95])
                        recv = int(qty * short)
                        # V11 overstates what it shipped on 40% of notices
                        asn_qty = recv + rng.choice([6, 12, 18, 24]) if v["vendor_id"] == "V11" and rng.random() < 0.4 else recv
                        ship_d = promised - timedelta(3)
                        asn.append({"asn_id": f"ASN{po_n:06d}", "po_number": po, "sku": s["sku"], "dc_id": dc,
                                    "ship_date": ship_d.isoformat(), "shipped_qty": asn_qty})
                        rd = promised + timedelta(late)
                        if rd <= DAYS[-1]:
                            pending.append({"receipt_id": f"R{po_n:06d}", "po_number": po, "sku": s["sku"], "dc_id": dc,
                                            "receipt_date": rd, "received_qty": recv})
        # occasional cycle-count adjustments
        if rng.random() < 0.3:
            st, s = rng.choice(STORES), rng.choice(skus)
            q = -min(on_hand[(st, s["sku"])], rng.randint(1, 2))
            if q:
                on_hand[(st, s["sku"])] += q
                event(datetime.combine(day, datetime.min.time()) + timedelta(hours=22), st, s["sku"], "ADJUSTMENT", q)
        # end-of-day snapshot
        for (loc, sku), q in on_hand.items():
            snaps.append({"snapshot_date": day.isoformat(), "location_id": loc, "sku": sku, "on_hand": q})
            if loc == "DC1" and day == date(2026, 5, 12):
                snaps.append({"snapshot_date": day.isoformat(), "location_id": loc, "sku": sku, "on_hand": q})  # double load

    rng.shuffle(events)  # the stream arrives in no particular order
    issues = [
        {"id": "I1", "type": "duplicate_snapshot_load", "detail": "DC1 inventory snapshot for 2026-05-12 was loaded twice."},
        {"id": "I2", "type": "vendor_short_ships_late", "vendor_id": "V07", "detail": "Short-ships 10-30% and arrives 3-9 days late."},
        {"id": "I3", "type": "asn_receipt_mismatch", "vendor_id": "V11", "detail": "Overstates shipped quantity on ~40% of ASNs."},
        {"id": "I4", "type": "stream_duplicates_and_late", "detail": "~1.5% duplicate events, ~2% late, delivered out of order."},
    ]
    write("vendors.csv", vendors); write("skus.csv", skus); write("locations.csv", locations)
    write("purchase_orders.csv", pos); write("asn.csv", asn); write("dc_receipts.csv", receipts)
    write("store_shipments.csv", ships); write("pos_sales.csv", sales); write("inventory_snapshots.csv", snaps)
    with open(OUT / "inventory_events.jsonl", "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    (OUT / "known_issues.json").write_text(json.dumps(issues, indent=1))
    return {k: len(v) for k, v in [("po", pos), ("asn", asn), ("receipts", receipts), ("ships", ships), ("sales", sales), ("snaps", snaps), ("events", events)]}


def write(name, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    print(main())
