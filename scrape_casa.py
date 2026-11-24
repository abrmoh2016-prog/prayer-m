#!/usr/bin/env python3
"""
Scraper für Gebetszeiten Casablanca (fm6oa.org)
Speichert HTML + JSON unter casa/
"""

import json
import os
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
    """Lädt HTML-Seite (mit User-Agent, sonst blocken manche Server)."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PrayerScraper/1.0)"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read()
    # fm6oa liefert UTF-8
    return raw.decode("utf-8", errors="replace")


def save_html(html: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_labelled(soup: BeautifulSoup, label: str) -> str:
    """
    Sucht in der Tabelle einen <td>/<th>, dessen Text exakt dem Label entspricht
    und gibt den Text der benachbarten Zelle zurück.
    """
    for cell in soup.find_all(["td", "th"]):
        if _clean(cell.get_text()) == label:
            sibling = cell.find_next_sibling(["td", "th"])
            if sibling:
                return _clean(sibling.get_text())
    return ""


def parse_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    data: dict = {
        "ville": "Casablanca",
        "ville_ar": "الدار البيضاء",
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
    }

    # ----- Date Hijri, Date Grégorienne, Heure -----
    data["date_hijri"] = _extract_labelled(soup, "Date Hijri")
    data["date_gregorienne"] = _extract_labelled(soup, "Date Grégorienne")
    data["heure"] = _extract_labelled(soup, "Heure")

    # ----- Nächste Prière (optional, aus "Prochaine Prière") -----
    prochaine = ""
    for tag in soup.find_all(string=re.compile(r"Prochaine Prière", re.I)):
        prochaine = _clean(tag.parent.get_text(" ", strip=True))
        break
    data["prochaine_priere_raw"] = prochaine

    # ----- Gebetszeiten aus div.prayerAdan -----
    prayer_div = soup.find("div", class_="prayerAdan")
    if not prayer_div:
        raise RuntimeError("div.prayerAdan nicht gefunden")

    # Variante A: innerhalb der div gibt es <td>/<th>-Zellen (Label + Zeit)
    times: dict = {}
    labels = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Ishae"]
    cells = prayer_div.find_all(["td", "th"])
    for i, cell in enumerate(cells):
        label = _clean(cell.get_text())
        if label in labels and i + 1 < len(cells):
            times[label] = _clean(cells[i + 1].get_text())

    # Variante B (Fallback): Text-Regex "Fajr 05:38 Dhuhr 12:22 ..."
    if len(times) < len(labels):
        text = _clean(prayer_div.get_text(" ", strip=True))
        for label in labels:
            m = re.search(rf"{label}\s*[:\s]\s*(\d{{1,2}}[:h]\d{{2}})", text)
            if m and label not in times:
                times[label] = m.group(1).replace("h", ":")

    if not times:
        raise RuntimeError("Keine Gebetszeiten im div.prayerAdan gefunden")

    data["gebetszeiten"] = {k: times.get(k, "") for k in labels}
    return data


def main() -> int:
    try:
        html = fetch_html(URL)
        save_html(html, HTML_FILE)
        print(f"[OK] HTML gespeichert: {HTML_FILE}")

        data = parse_html(html)
        JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
        JSON_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OK] JSON gespeichert: {JSON_FILE}")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(f"[FEHLER] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())