#!/usr/bin/env python3
"""Scraper for Casablanca prayer times (fm6oa.org)."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

URL = "https://fm6oa.org/prieres/code/index-fr.php?ville=15"
BASE_DIR = Path("casa")
HTML_FILE = BASE_DIR / "casablanca.html"
JSON_FILE = BASE_DIR / "casa.json"


def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PrayerScraper/1.0)"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def parse_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    data = {
        "ville": "Casablanca",
        "ville_ar": "الدار البيضاء",
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
    }

    # 1. Datum und Uhrzeit aus der obersten Tabelle holen
    # Wir suchen alle Tabellenzellen (td/th) auf der Seite
    cells = soup.find_all(["td", "th"])
    
    for i, cell in enumerate(cells):
        text = cell.get_text(strip=True)
        
        # Hijri Datum
        if "Date Hijri" in text and i + 1 < len(cells):
            data["date_hijri"] = cells[i + 1].get_text(strip=True)
        
        # Gregorianisches Datum
        elif "Date Grégorienne" in text and i + 1 < len(cells):
            data["date_gregorienne"] = cells[i + 1].get_text(strip=True)
            
        # Uhrzeit
        elif "Heure" in text and i + 1 < len(cells):
            data["heure"] = cells[i + 1].get_text(strip=True)

    # 2. Gebetszeiten aus div.prayerAdan holen
    prayer_div = soup.find("div", class_="prayerAdan")
    if not prayer_div:
        raise RuntimeError("div.prayerAdan not found")

    labels = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Ishae"]
    times = {}

    # Wir suchen alle Zellen (td) innerhalb der Gebetszeiten-Div
    prayer_cells = prayer_div.find_all("td")
    
    # Wir gehen die Zellen durch und suchen nach den Uhrzeiten
    for i, cell in enumerate(prayer_cells):
        text = cell.get_text(strip=True)
        
        # Wenn die Zelle eine Uhrzeit enthält (z.B. 05:38)
        if re.match(r"^\d{1,2}:\d{2}$", text):
            # Die Zelle davor sollte das Label sein (z.B. "Fajr")
            if i > 0:
                label = prayer_cells[i - 1].get_text(strip=True)
                if label in labels:
                    times[label] = text

    # Fallback: Falls die Struktur anders ist, suchen wir im Text der Div
    if not times:
        div_text = prayer_div.get_text(" ", strip=True)
        for label in labels:
            # Sucht z.B. "Fajr 05:38" oder "Fajr: 05:38"
            m = re.search(rf"{label}\s*[:\-]?\s*(\d{{1,2}}:\d{{2}})", div_text, re.IGNORECASE)
            if m:
                times[label] = m.group(1)

    # Standardwerte setzen, falls etwas fehlt
    data["gebetszeiten"] = {k: times.get(k, "") for k in labels}
    
    return data


def main() -> int:
    try:
        html = fetch_html(URL)
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        HTML_FILE.write_text(html, encoding="utf-8")
        print(f"[OK] HTML saved: {HTML_FILE}")

        data = parse_html(html)
        JSON_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] JSON saved: {JSON_FILE}")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
