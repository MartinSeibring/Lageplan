"""Themenradar-Aktualisierung.

Liest config.json (Keywords + RSS-Feeds), ruft die Feeds ab, gleicht
Titel/Beschreibung gegen die Keywords ab und schreibt Vorschläge nach
data/radar-vorschlaege.json sowie den Zeitstempel nach data/last_run.json.

Läuft in GitHub Actions (.github/workflows/update-radar.yml) — nutzt nur
die Python-Standardbibliothek, keine externen Pakete nötig.
"""

import json
import os
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH      = os.path.join(BASE_DIR, "config.json")
THEMEN_PATH      = os.path.join(BASE_DIR, "data", "themen.json")
VORSCHLAEGE_PATH = os.path.join(BASE_DIR, "data", "radar-vorschlaege.json")
GESEHEN_PATH     = os.path.join(BASE_DIR, "data", "radar-gesehen.json")
LAST_RUN_PATH    = os.path.join(BASE_DIR, "data", "last_run.json")

MAX_GESEHEN = 500  # Merkliste alter Links begrenzen

# Cluster-Zuordnung anhand von Schlagworten im Text
CLUSTER_REGELN = {
    "Netzanschluss":      ["netzanschluss", "anschlussbegehren", "wärmepumpe",
                           "ladeeinrichtung", "wallbox", "einspeis"],
    "Messstellenbetrieb": ["messstellen", "smart meter", "intelligente messsysteme",
                           "zähler", "rollout", "msbg"],
    "Netzwirtschaft":     ["netzentgelt", "anreizregulierung", "eigenkapital",
                           "regulierung", "redispatch", "erlösobergrenze", "aregv"],
    "Technologie":        ["digitalisierung", "ki ", "künstliche intelligenz",
                           "smart grid", "flexibilität", "14a"],
    "Organisation":       ["personal", "fachkräfte", "organisation"],
}

KATEGORIE_REGELN = [
    ("regulatorisch",  ["festlegung", "verordnung", "gesetz", "§", "enwg",
                        "msbg", "aregv", "beschluss", "konsultation"]),
    ("technologisch",  ["smart meter", "digitalisierung", "smart grid",
                        "künstliche intelligenz", "technologie"]),
    ("marktlich",      ["markt", "preis", "beschaffung", "vergütung", "auktion"]),
    ("wettbewerblich", ["wettbewerb", "konzession"]),
]


def lade_json(pfad, default):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def hole_feed(url):
    """Feed abrufen und als XML-Baum liefern (None bei Fehler)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Lageplan-Radar)"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return ET.fromstring(resp.read())
    except Exception as e:
        print(f"  FEHLER beim Abruf {url}: {e}")
        return None


def feed_items(baum):
    """RSS- und Atom-Einträge vereinheitlichen: (titel, beschreibung, link, datum)."""
    eintraege = []
    # RSS 2.0
    for item in baum.iter("item"):
        titel = (item.findtext("title") or "").strip()
        besch = re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip()
        link  = (item.findtext("link") or "").strip()
        datum = (item.findtext("pubDate") or "").strip()
        eintraege.append((titel, besch, link, datum))
    # Atom
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in baum.iter(f"{ns}entry"):
        titel = (entry.findtext(f"{ns}title") or "").strip()
        besch = re.sub(r"<[^>]+>", " ", entry.findtext(f"{ns}summary") or "").strip()
        link_el = entry.find(f"{ns}link")
        link  = link_el.get("href", "") if link_el is not None else ""
        datum = (entry.findtext(f"{ns}updated") or "").strip()
        eintraege.append((titel, besch, link, datum))
    return eintraege


def parse_datum(roh):
    """Feed-Datum in YYYY-MM-DD wandeln, sonst leer."""
    if not roh:
        return ""
    try:
        return parsedate_to_datetime(roh).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(roh.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def finde_cluster(text):
    treffer = [c for c, worte in CLUSTER_REGELN.items()
               if any(w in text for w in worte)]
    return treffer or ["Netzwirtschaft"]


def finde_kategorie(text):
    for kat, worte in KATEGORIE_REGELN:
        if any(w in text for w in worte):
            return kat
    return "regulatorisch"  # Behörden-Feeds → Standard


def main():
    config   = lade_json(CONFIG_PATH, {})
    keywords = config.get("keywords", [])
    feeds    = config.get("rss_feeds", [])
    min_treffer = int(config.get("min_keyword_treffer", 1))

    # themen.json ist eine Top-Level-Liste; {"themen": [...]} wird ebenfalls unterstützt
    themen_roh = lade_json(THEMEN_PATH, [])
    themen = themen_roh.get("themen", []) if isinstance(themen_roh, dict) else themen_roh
    bekannte_titel = {t.get("titel", "").strip().lower() for t in themen}

    gesehen = set(lade_json(GESEHEN_PATH, {}).get("links", []))

    vorschlaege = []
    neu_gesehen = []

    for feed in feeds:
        if feed.get("aktiv") is False:
            continue
        name, url = feed.get("name", "Quelle"), feed.get("url", "")
        print(f"Feed: {name}")
        baum = hole_feed(url)
        if baum is None:
            continue

        for titel, besch, link, datum_roh in feed_items(baum):
            if not titel or (link and link in gesehen):
                continue
            text = f"{titel} {besch}".lower()

            gefunden = [kw for kw in keywords if kw.lower() in text]
            if len(gefunden) < min_treffer:
                continue
            if titel.strip().lower() in bekannte_titel:
                continue

            vorschlaege.append({
                "titel":                       titel[:150],
                "zusammenfassung":             besch[:400],
                "begruendung":                 "Keywords: " + ", ".join(gefunden[:5]),
                "name":                        name,
                "link":                        link,
                "datum":                       parse_datum(datum_roh),
                "vorgeschlagene_kategorie":    finde_kategorie(text),
                "vorgeschlagener_zeithorizont": "kurzfristig",
                "vorgeschlagene_auswirkung":   3,
                "vorgeschlagene_cluster":      finde_cluster(text),
                "vorgeschlagene_tags":         gefunden[:5],
            })
            if link:
                neu_gesehen.append(link)
            print(f"  + {titel[:70]}")

    jetzt = datetime.now(timezone.utc).isoformat()

    os.makedirs(os.path.dirname(VORSCHLAEGE_PATH), exist_ok=True)
    with open(VORSCHLAEGE_PATH, "w", encoding="utf-8") as f:
        json.dump({"erstellt": jetzt, "vorschlaege": vorschlaege},
                  f, ensure_ascii=False, indent=2)

    alle_links = (list(gesehen) + neu_gesehen)[-MAX_GESEHEN:]
    with open(GESEHEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"links": alle_links}, f, ensure_ascii=False, indent=2)

    with open(LAST_RUN_PATH, "w", encoding="utf-8") as f:
        json.dump({"letzter_lauf": jetzt, "anzahl_vorschlaege": len(vorschlaege)},
                  f, ensure_ascii=False, indent=2)

    print(f"\nFertig: {len(vorschlaege)} Vorschläge → {VORSCHLAEGE_PATH}")


if __name__ == "__main__":
    main()
