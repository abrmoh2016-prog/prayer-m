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
        "date_hijri": "",
        "date_gregorienne": "",
        "heure": ""
    }

    # 1. Datum und Uhrzeit aus der linken Tabelle (prayer-today)
    today_div = soup.find("div", class_="prayer-today")
    if today_div:
        rows = today_div.find_all("tr")
        for row in rows:
            th = row.find("th")
            td = row.find("td")
            if th and td:
                label = th.get_text(strip=True)
                if label == "Date Hijri":
                    data["date_hijri"] = td.get_text(strip=True) or "Nicht verfügbar (JS)"
                elif label == "Date Grégorienne":
                    data["date_gregorienne"] = td.get_text(strip=True)
                elif label == "Heure":
                    # Uhrzeit wird per JS geladen. Wenn leer, nutzen wir die aktuelle Serverzeit
                    time_text = td.get_text(strip=True)
                    data["heure"] = time_text if time_text else datetime.now().strftime("%H:%M:%S")

    # 2. Gebetszeiten aus div.prayerAdan
    prayer_div = soup.find("div", class_="prayerAdan")
    if not prayer_div:
        raise RuntimeError("div.prayerAdan not found")

    labels = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Ishae"]
    times = {}

    # Wir holen uns die Kopfzeile (th) und die Datenzeile (td)
    headers = prayer_div.find_all("th")
    values = prayer_div.find_all("td")

    # Sicherstellen, dass wir gleich viele Spalten haben
    if len(headers) == len(values):
        for h, v in zip(headers, values):
            label = h.get_text(strip=True)
            val = v.get_text(strip=True)
            if label in labels:
                times[label] = val
    else:
        # Fallback, falls die Struktur unerwartet ist
        div_text = prayer_div.get_text(" ", strip=True)
        for label in labels:
            m = re.search(rf"{label}\s*(\d{{1,2}}:\d{{2}})", div_text, re.IGNORECASE)
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
