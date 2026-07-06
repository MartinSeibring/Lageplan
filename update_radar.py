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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
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
    "Technologie":        ["digitalisierung", "künstliche intelligenz",
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
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Encoding": "identity",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            roh = resp.read()
    except Exception as e:
        print(f"  FEHLER beim Abruf {url}: {e}")
        return None
    # BOM und führende Leerzeilen entfernen (BMWK liefert Leerzeile vor <?xml)
    if roh.startswith(b"\xef\xbb\xbf"):
        roh = roh[3:]
    roh = roh.lstrip()
    try:
        return ET.fromstring(roh)
    except ET.ParseError as e:
        anfang = roh[:120].decode("utf-8", errors="replace")
        print(f"  FEHLER beim Parsen {url}: {e}")
        print(f"    Antwort beginnt mit: {anfang!r}")
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
    bekannte_titel = {(t.get("titel") or "").strip().lower() for t in themen}

    # Themen-Beobachtung: explizite Beobachtungs-Begriffe je Thema,
    # ohne Eintrag dienen die Tags als Fallback. Treffer werden als
    # Update-Vorschlag dem Thema zugeordnet statt als neues Thema.
    beobachtete = []
    for t in themen:
        begriffe = [b.strip() for b in (t.get("beobachtung") or []) if len(b.strip()) >= 4]
        explizit = bool(begriffe)
        if not begriffe:
            begriffe = [b.strip() for b in (t.get("tags") or []) if len(b.strip()) >= 4]
        if begriffe and t.get("id") is not None:
            beobachtete.append({"id": t["id"], "titel": t.get("titel") or "",
                                "begriffe": begriffe, "explizit": explizit})

    gesehen = set(lade_json(GESEHEN_PATH, {}).get("links", []))

    vorschlaege = []
    neu_gesehen = []

    def verarbeite(name, baum, erzwungenes_kw=None, limit=None, max_alter_tage=None):
        """Feed-Einträge gegen Keywords prüfen und als Vorschläge sammeln.

        erzwungenes_kw: bei Google-News-Suchfeeds zählt das gesuchte Keyword
        immer als Treffer (es steht oft nur im Artikeltext, nicht im Titel).
        limit begrenzt neue Vorschläge pro Feed, max_alter_tage das Artikelalter.
        """
        anzahl = 0
        for titel, besch, link, datum_roh in feed_items(baum):
            if not titel:
                continue
            dkey = link or ("titel:" + titel.strip().lower())
            if dkey in gesehen:
                continue
            datum = parse_datum(datum_roh)
            if max_alter_tage and datum:
                grenze = datetime.now(timezone.utc) - timedelta(days=max_alter_tage)
                if datum < grenze.strftime("%Y-%m-%d"):
                    continue
            text = f"{titel} {besch}".lower()

            # Themen-Beobachtung: Treffer wird dem bestehenden Thema
            # als Update zugeordnet (kein neuer Themen-Vorschlag)
            update_thema, update_begriff = None, None
            for b in beobachtete:
                for begriff in b["begriffe"]:
                    if begriff.lower() in text:
                        update_thema, update_begriff = b, begriff
                        break
                if update_thema:
                    break
            if update_thema:
                vorschlaege.append({
                    "titel":                  titel[:150],
                    "zusammenfassung":        besch[:400],
                    "begruendung":            f'Beobachtung "{update_begriff}"',
                    "name":                   name,
                    "link":                   link,
                    "datum":                  datum,
                    "update_fuer_thema_id":   update_thema["id"],
                    "update_fuer_thema_titel": update_thema["titel"],
                })
                neu_gesehen.append(dkey)
                gesehen.add(dkey)
                print(f"  ↻ {titel[:60]} → Thema: {update_thema['titel'][:40]}")
                anzahl += 1
                if limit and anzahl >= limit:
                    break
                continue

            gefunden = [kw for kw in keywords if kw.lower() in text]
            if erzwungenes_kw and erzwungenes_kw not in gefunden:
                gefunden.append(erzwungenes_kw)
            if len(gefunden) < (1 if erzwungenes_kw else min_treffer):
                continue
            if titel.strip().lower() in bekannte_titel:
                continue

            vorschlaege.append({
                "titel":                       titel[:150],
                "zusammenfassung":             besch[:400],
                "begruendung":                 ("Google-News-Suche: " + erzwungenes_kw
                                                if erzwungenes_kw
                                                else "Keywords: " + ", ".join(gefunden[:5])),
                "name":                        name,
                "link":                        link,
                "datum":                       datum,
                "vorgeschlagene_kategorie":    finde_kategorie(text),
                "vorgeschlagener_zeithorizont": "kurzfristig",
                "vorgeschlagene_auswirkung":   3,
                "vorgeschlagene_cluster":      finde_cluster(text),
                "vorgeschlagene_tags":         gefunden[:5],
            })
            neu_gesehen.append(dkey)
            gesehen.add(dkey)  # verhindert Dubletten im selben Lauf
            print(f"  + {titel[:70]}")
            anzahl += 1
            if limit and anzahl >= limit:
                break

    # ── Stufe 1: konfigurierte RSS-Feeds ──────────────────────────
    for feed in feeds:
        if feed.get("aktiv") is False:
            continue
        name, url = feed.get("name", "Quelle"), feed.get("url", "")
        print(f"Feed: {name}")
        baum = hole_feed(url)
        if baum is not None:
            verarbeite(name, baum)

    # ── Stufe 2: globale Google-News-Suche pro Keyword ────────────
    # Für jedes Keyword wird der Google-News-Suchfeed abgefragt
    # (deutschsprachige Nachrichten, letzte 14 Tage, max. 3 neue
    # Vorschläge pro Keyword und Lauf).
    if config.get("google_news_suche", True):
        for kw in keywords:
            url = ("https://news.google.com/rss/search?q=" +
                   urllib.parse.quote(kw) + "&hl=de&gl=DE&ceid=DE:de")
            print(f"Google News: {kw}")
            baum = hole_feed(url)
            if baum is not None:
                verarbeite(f"Google News: {kw}", baum,
                           erzwungenes_kw=kw, limit=3, max_alter_tage=14)

        # Gezielte Suche nach expliziten Beobachtungs-Begriffen der Themen
        # (Tags-Fallback loest bewusst KEINE eigene Suche aus, sonst wird
        # das Suchvolumen zu gross - Tags matchen nur gegen obige Treffer)
        gesucht = []
        for b in beobachtete:
            if b["explizit"]:
                for begriff in b["begriffe"]:
                    if begriff.lower() not in [g.lower() for g in gesucht]:
                        gesucht.append(begriff)
        for begriff in gesucht[:15]:
            url = ("https://news.google.com/rss/search?q=" +
                   urllib.parse.quote(begriff) + "&hl=de&gl=DE&ceid=DE:de")
            print(f"Google News (Beobachtung): {begriff}")
            baum = hole_feed(url)
            if baum is not None:
                verarbeite(f"Google News: {begriff}", baum,
                           erzwungenes_kw=begriff, limit=3, max_alter_tage=14)

    jetzt = datetime.now(timezone.utc).isoformat()

    # Bestehende (noch nicht bearbeitete) Vorschläge behalten - neue kommen
    # nach vorn, Duplikate per Link aussortiert, Gesamtliste begrenzt
    alte = lade_json(VORSCHLAEGE_PATH, {}).get("vorschlaege", [])
    def _vkey(v):
        return v.get("link") or ("titel:" + (v.get("titel") or "").strip().lower())
    neue_keys = {_vkey(v) for v in vorschlaege}
    behalten = [v for v in alte if _vkey(v) not in neue_keys]
    vorschlaege = (vorschlaege + behalten)[:50]

    os.makedirs(os.path.dirname(VORSCHLAEGE_PATH), exist_ok=True)
    with open(VORSCHLAEGE_PATH, "w", encoding="utf-8") as f:
        json.dump({"erstellt": jetzt, "vorschlaege": vorschlaege},
                  f, ensure_ascii=False, indent=2)

    alte_links = lade_json(GESEHEN_PATH, {}).get("links", [])
    alt_set = set(alte_links)
    alle_links = (alte_links + [l for l in neu_gesehen if l not in alt_set])[-MAX_GESEHEN:]
    with open(GESEHEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"links": alle_links}, f, ensure_ascii=False, indent=2)

    with open(LAST_RUN_PATH, "w", encoding="utf-8") as f:
        json.dump({"letzter_lauf": jetzt, "anzahl_vorschlaege": len(vorschlaege)},
                  f, ensure_ascii=False, indent=2)

    print(f"\nFertig: {len(vorschlaege)} Vorschläge → {VORSCHLAEGE_PATH}")


if __name__ == "__main__":
    main()
