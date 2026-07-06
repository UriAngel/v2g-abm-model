"""Build a CSV of one year of GB wholesale prices from BMRS.

Pulls 25 June 2025 -> 25 June 2026 from the Elexon API, APX MID
provider, drops zero-price rows, writes a clean CSV with columns:
  settlement_date, settlement_period, hour_of_day, price_gbp_per_mwh,
  price_gbp_per_kwh.

The CSV is the data source for the simulator's hour-by-hour wholesale
tariff (uk_wholesale_price_at_hour_of_year); the static
UK_WHOLESALE_24H_GBP array remains for typical-day plots.

Run:  python -m src.build_bmrs_year_csv
"""

from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import csv
import json
import urllib.request


START = datetime(2025, 6, 25)
END   = datetime(2026, 6, 25)
CHUNK_DAYS = 7
API = "https://data.elexon.co.uk/bmrs/api/v1/balancing/pricing/market-index"

OUT = Path(__file__).resolve().parent.parent / "data" / "uk_wholesale_2025_2026.csv"


def fetch_chunk(t0: datetime, t1: datetime, retries: int = 3) -> list[dict]:
    url = (f"{API}?from={t0.strftime('%Y-%m-%dT%H:%MZ')}"
           f"&to={t1.strftime('%Y-%m-%dT%H:%MZ')}&format=json")
    last_err: Exception | None = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                payload = json.load(r)
            return [x for x in payload["data"]
                    if x["dataProvider"] == "APXMIDP" and x["price"] > 0]
        except Exception as e:
            last_err = e
    raise RuntimeError(f"BMRS fetch failed: {last_err}\nURL: {url}")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    cur = START
    while cur < END:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), END)
        chunk = fetch_chunk(cur, nxt)
        rows.extend(chunk)
        print(f"  fetched {cur.date()} -> {nxt.date()} ({len(chunk):4d} rows, "
              f"cumulative {len(rows):5d})")
        cur = nxt

    # De-duplicate (BMRS occasionally returns same (date, period) twice)
    seen = set()
    unique: list[dict] = []
    for r in rows:
        key = (r["settlementDate"], r["settlementPeriod"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    # Sort chronologically
    unique.sort(key=lambda r: (r["settlementDate"], r["settlementPeriod"]))

    # Write CSV
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["settlement_date", "settlement_period", "hour_of_day",
                    "price_gbp_per_mwh", "price_gbp_per_kwh"])
        for r in unique:
            sp = r["settlementPeriod"]
            hour = (sp - 1) // 2
            price_mwh = r["price"]
            price_kwh = price_mwh / 1000.0
            w.writerow([r["settlementDate"], sp, hour, price_mwh, f"{price_kwh:.6f}"])

    print()
    print(f"Saved {len(unique):,} rows to {OUT}")
    print(f"Date range: {unique[0]['settlementDate']} -> {unique[-1]['settlementDate']}")
    annual_mean = sum(r["price"] for r in unique) / len(unique) / 10.0
    print(f"Annual mean: {annual_mean:.3f} p/kWh")


if __name__ == "__main__":
    main()
