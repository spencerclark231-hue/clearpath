"""Pull the raw public datasets straight from their publishers.

    python scripts/fetch_data.py

Writes to data/raw/live/:
  portwatch_chokepoints_database.csv   IMF PortWatch chokepoint reference table (28 rows)
  portwatch_daily_chokepoints.csv      IMF PortWatch daily transit calls, last N days, all chokepoints
  worldbank_lpi_2023.csv               World Bank LPI overall score (WDI LP.LPI.OVRL.XQ, stored as 2022)
  nyfed_gscpi.csv                      NY Fed Global Supply Chain Pressure Index, monthly since 1997

Use these files to verify or refresh data/raw/ and then rebuild the documents:
    python scripts/build_knowledge_base.py && python scripts/ingest.py
Needs internet access. GSCPI parsing needs pandas + openpyxl.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "live"
ARC = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
DAYS = 180


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "clearpath-student-project/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def arcgis_all(layer: str, where: str = "1=1") -> list[dict]:
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"where": where, "outFields": "*", "returnGeometry": "false", "f": "json",
                                    "resultOffset": offset, "resultRecordCount": 1000})
        data = json.loads(get(f"{ARC}/{layer}/FeatureServer/0/query?{q}"))
        feats = [f["attributes"] for f in data.get("features", [])]
        rows += feats
        if not data.get("exceededTransferLimit") or not feats:
            return rows
        offset += len(feats)


def write(name: str, rows: list[dict]) -> None:
    if not rows:
        print(f"  ! {name}: no rows")
        return
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  ✓ {name}: {len(rows)} rows")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []

    def job(fn):
        jobs.append(fn)
        return fn

    @job
    def chokepoints():
        write("portwatch_chokepoints_database.csv", arcgis_all("PortWatch_chokepoints_database"))

    @job
    def daily():
        since = (date.today() - timedelta(days=DAYS)).isoformat()
        write("portwatch_daily_chokepoints.csv", arcgis_all("Daily_Chokepoints_Data", f"date >= DATE '{since}'"))

    @job
    def lpi():
        data = json.loads(get("https://api.worldbank.org/v2/country/all/indicator/LP.LPI.OVRL.XQ"
                              "?date=2022&format=json&per_page=400"))
        rows = [{"entity": d["country"]["value"], "iso3": d["countryiso3code"], "lpi_overall_score": d["value"]}
                for d in data[1] if d["value"] is not None]
        write("worldbank_lpi_2023.csv", rows)

    @job
    def gscpi():
        import pandas as pd
        raw = get("https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx")
        df = pd.read_excel(io.BytesIO(raw), sheet_name="GSCPI Monthly Data")
        df = df.iloc[:, :2].dropna()
        df.columns = ["month", "gscpi"]
        write("nyfed_gscpi.csv", [{"month": str(m)[:7], "gscpi": round(float(v), 4)} for m, v in df.values])

    failed = 0
    for fn in jobs:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ✗ {fn.__name__}: {type(e).__name__}: {e}")
    sys.exit(1 if failed == len(jobs) else 0)


if __name__ == "__main__":
    main()
