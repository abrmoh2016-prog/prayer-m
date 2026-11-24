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

    # 1. Datum und Uhrzeit extrahieren (sucht nach den Labels und holt den Text danach)
    text_content = soup.get_text(" ", strip=True)
    
    hijri_match = re.search(r"Date Hijri\s*([^\n|]+?)(?:\s*Date Grégorienne|\s*Heure|$)", text_content, re.IGNORECASE)
    data["date_hijri"] = hijri_match.group(1).strip() if hijri_match else ""

    greg_match = re.search(r"Date Grégorienne\s*([^\n|]+?)(?:\s*Heure|$)", text_content, re.IGNORECASE)
    data["date_gregorienne"] = greg_match.group(1).strip() if greg_match else ""

    heure_match = re.search(r"Heure\s*(\d{2}:\d{2}:\d{2})", text_content, re.IGNORECASE)
    data["heure"] = heure_match.group(1).strip() if heure_match else ""

    # 2. Gebetszeiten aus div.prayerAdan extrahieren
    prayer_div = soup.find("div", class_="prayerAdan")
    if not prayer_div:
        raise RuntimeError("div.prayerAdan not found")

    # Wir holen uns den reinen Text aus der div
    prayer_text = prayer_div.get_text(" ", strip=True)
    
    # Regex sucht nach "Label" gefolgt von einer Zeit (z.B. 05:38)
    labels = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Ishae"]
    times = {}
    
    for label in labels:
        # Sucht z.B. "Fajr 05:38" oder "Fajr : 05:38"
        m = re.search(rf"{label}\s*[:\-]?\s*(\d{{1,2}}[:h]\d{{2}})", prayer_text, re.IGNORECASE)
        if m:
            times[label] = m.group(1).replace("h", ":")
        else:
            times[label] = ""

    # Wenn die Regex fehlschlägt, versuchen wir es mit der alten Methode (Zellen parsen)
    if not any(times.values()):
        cells = prayer_div.find_all(["td", "th"])
        for i, cell in enumerate(cells):
            label = cell.get_text(strip=True)
            if label in labels and i + 1 < len(cells):
                times[label] = cells[i + 1].get_text(strip=True)

    data["gebetszeiten"] = times
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
