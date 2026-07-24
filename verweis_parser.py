#!/usr/bin/env python3
"""
Extrahiert Querverweise zwischen Gesetzen aus den XML-Volltexten
von gesetze-im-internet.de und erzeugt daraus das JSON-Datenmodell
fuer die Netzvisualisierung (normennetz.html).

WARUM DIESES SKRIPT:
Die Netzvisualisierung enthaelt eine kuratierte Auswahl strukturbildender
Verweise. Fuer Vollstaendigkeit muessen die Verweise maschinell aus den
Gesetzestexten extrahiert werden. Das geht nur lokal, weil die Portale
automatisierten Zugriff blockieren.

VORBEREITUNG (einmalig, manuell):
1. Auf https://www.gesetze-im-internet.de das jeweilige Gesetz oeffnen
2. Unten "XML" herunterladen (Link "xml" neben "HTML"/"PDF")
   Direktmuster: https://www.gesetze-im-internet.de/<kuerzel>/xml.zip
   z.B. messbg/xml.zip, enwg_2005/xml.zip, eeg_2023/xml.zip
3. Alle ZIPs in einen Ordner entpacken, z.B. ./gesetze/
4. python3 verweis_parser.py ./gesetze --out verweise.json

ABHAENGIGKEITEN: nur Standardbibliothek.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------
# Normenregister: Kuerzel -> Anzeigename + Ebene
# Erweiterbar. Der Key ist das, was im Gesetzestext als Zitat auftaucht.
# ---------------------------------------------------------------
NORMEN = {
    "MsbG":            {"label": "MsbG",       "full": "Messstellenbetriebsgesetz",        "level": "gesetz"},
    "EnWG":            {"label": "EnWG",       "full": "Energiewirtschaftsgesetz",          "level": "gesetz"},
    "EEG":             {"label": "EEG 2023",   "full": "Erneuerbare-Energien-Gesetz",       "level": "gesetz"},
    "KWKG":            {"label": "KWKG",       "full": "Kraft-Waerme-Kopplungsgesetz",      "level": "gesetz"},
    "BSIG":            {"label": "BSIG",       "full": "BSI-Gesetz",                        "level": "gesetz"},
    "MessEG":          {"label": "MessEG",     "full": "Mess- und Eichgesetz",              "level": "gesetz"},
    "MessEV":          {"label": "MessEV",     "full": "Mess- und Eichverordnung",          "level": "verordnung"},
    "StromNZV":        {"label": "StromNZV",   "full": "Stromnetzzugangsverordnung",        "level": "verordnung"},
    "StromNEV":        {"label": "StromNEV",   "full": "Stromnetzentgeltverordnung",        "level": "verordnung"},
    "NAV":             {"label": "NAV",        "full": "Niederspannungsanschlussverordnung","level": "verordnung"},
    "StromGVV":        {"label": "StromGVV",   "full": "Stromgrundversorgungsverordnung",   "level": "verordnung"},
    "EnFG":            {"label": "EnFG",       "full": "Energiefinanzierungsgesetz",        "level": "gesetz"},
    "GEG":             {"label": "GEG",        "full": "Gebaeudeenergiegesetz",             "level": "gesetz"},
    "BDSG":            {"label": "BDSG",       "full": "Bundesdatenschutzgesetz",           "level": "gesetz"},
    "DSGVO":           {"label": "DSGVO",      "full": "Datenschutz-Grundverordnung",       "level": "eu"},
}

# Dateiname (ohne Endung) -> Normkuerzel. Ergaenzen, falls anders benannt.
DATEI_ZU_NORM = {
    "messbg":     "MsbG",
    "enwg_2005":  "EnWG",
    "eeg_2023":   "EEG",
    "eeg_2014":   "EEG",
    "kwkg_2016":  "KWKG",
    "bsig_2009":  "BSIG",
    "messeg":     "MessEG",
    "messev":     "MessEV",
    "stromnzv":   "StromNZV",
    "stromnev":   "StromNEV",
    "nav":        "NAV",
    "stromgvv":   "StromGVV",
    "enfg":       "EnFG",
    "geg":        "GEG",
    "bdsg_2018":  "BDSG",
}

# ---------------------------------------------------------------
# Verweismuster
# Faengt: "§ 14a des Energiewirtschaftsgesetzes", "§ 9 EEG",
#         "§§ 21 bis 25 des Messstellenbetriebsgesetzes", "Artikel 6 DSGVO"
# ---------------------------------------------------------------
LANGNAMEN = {
    r"Energiewirtschaftsgesetz(?:es)?":              "EnWG",
    r"Messstellenbetriebsgesetz(?:es)?":             "MsbG",
    r"Erneuerbare-Energien-Gesetz(?:es)?":           "EEG",
    r"Kraft-W(?:ä|ae)rme-Kopplungsgesetz(?:es)?":    "KWKG",
    r"BSI-Gesetz(?:es)?":                            "BSIG",
    r"Mess- und Eichgesetz(?:es)?":                  "MessEG",
    r"Mess- und Eichverordnung":                     "MessEV",
    r"Stromnetzzugangsverordnung":                   "StromNZV",
    r"Stromnetzentgeltverordnung":                   "StromNEV",
    r"Niederspannungsanschlussverordnung":           "NAV",
    r"Stromgrundversorgungsverordnung":              "StromGVV",
    r"Energiefinanzierungsgesetz(?:es)?":            "EnFG",
    r"Geb(?:ä|ae)udeenergiegesetz(?:es)?":           "GEG",
    r"Bundesdatenschutzgesetz(?:es)?":               "BDSG",
    r"Verordnung \(EU\) 2016/679":                   "DSGVO",
}

PARA = r"(§§?\s*\d+[a-z]?(?:\s*(?:bis|und|,)\s*\d+[a-z]?)*|Artikel\s+\d+[a-z]?|Art\.\s*\d+[a-z]?)"

def baue_muster():
    """Erzeugt (regex, zielnorm) fuer Lang- und Kurzformen."""
    muster = []
    for lang, kuerzel in LANGNAMEN.items():
        # "§ 14a des Energiewirtschaftsgesetzes"
        muster.append((re.compile(PARA + r"\s+(?:des|der)\s+" + lang), kuerzel))
        # "Energiewirtschaftsgesetz ... § 14a" umgekehrt selten -> weggelassen
    for kuerzel in NORMEN:
        # "§ 9 EEG" / "§ 25 MsbG"
        esc = re.escape(kuerzel)
        muster.append((re.compile(PARA + r"\s+" + esc + r"\b"), kuerzel))
    return muster

MUSTER = baue_muster()


def text_aus_xml(pfad: Path) -> str:
    """Zieht den gesamten Textinhalt aus der XML-Datei."""
    try:
        baum = ET.parse(pfad)
    except ET.ParseError as e:
        print(f"  ! XML-Fehler in {pfad.name}: {e}", file=sys.stderr)
        return ""
    return " ".join(t.strip() for t in baum.getroot().itertext() if t and t.strip())


def norm_aus_dateiname(pfad: Path) -> str | None:
    stamm = pfad.stem.lower()
    if stamm in DATEI_ZU_NORM:
        return DATEI_ZU_NORM[stamm]
    for schluessel, norm in DATEI_ZU_NORM.items():
        if stamm.startswith(schluessel):
            return norm
    return None


def extrahiere(ordner: Path):
    """Liest alle XML-Dateien und zaehlt Verweise pro Normpaar."""
    kanten = defaultdict(lambda: {"anzahl": 0, "fundstellen": []})
    gefunden = []

    dateien = sorted(ordner.rglob("*.xml"))
    if not dateien:
        print(f"Keine XML-Dateien in {ordner} gefunden.", file=sys.stderr)
        return kanten, gefunden

    for datei in dateien:
        quelle = norm_aus_dateiname(datei)
        if not quelle:
            print(f"  ? Unbekannte Datei, uebersprungen: {datei.name}", file=sys.stderr)
            continue
        gefunden.append(quelle)
        text = text_aus_xml(datei)
        if not text:
            continue
        print(f"  - {datei.name} -> {quelle} ({len(text):,} Zeichen)")

        for regex, ziel in MUSTER:
            if ziel == quelle:
                continue  # Eigenverweise ignorieren
            for treffer in regex.finditer(text):
                schluessel = (quelle, ziel)
                kanten[schluessel]["anzahl"] += 1
                if len(kanten[schluessel]["fundstellen"]) < 8:
                    kanten[schluessel]["fundstellen"].append(treffer.group(0).strip())

    return kanten, gefunden


def baue_json(kanten, gefunden, min_treffer: int):
    knoten_ids = set(gefunden)
    for (q, z) in kanten:
        knoten_ids.add(q); knoten_ids.add(z)

    knoten = []
    for kid in sorted(knoten_ids):
        meta = NORMEN.get(kid, {"label": kid, "full": kid, "level": "gesetz"})
        knoten.append({"id": kid, "label": meta["label"], "full": meta["full"], "level": meta["level"]})

    links = []
    for (q, z), daten in sorted(kanten.items(), key=lambda x: -x[1]["anzahl"]):
        if daten["anzahl"] < min_treffer:
            continue
        # Erste vier eindeutige Fundstellen als Beispiel, Reihenfolge erhalten.
        beispiele = ", ".join(list(dict.fromkeys(daten["fundstellen"]))[:4])
        links.append({
            "source": q,
            "target": z,
            "anzahl": daten["anzahl"],
            "what": f"{daten['anzahl']} Verweis(e) im Volltext gefunden",
            "ref": beispiele
        })
    return {"nodes": knoten, "links": links}


def main():
    ap = argparse.ArgumentParser(description="Extrahiert Gesetzesquerverweise aus XML-Volltexten.")
    ap.add_argument("ordner", type=Path, help="Ordner mit entpackten XML-Dateien")
    ap.add_argument("--out", type=Path, default=Path("verweise.json"), help="Zieldatei (JSON)")
    ap.add_argument("--min", type=int, default=1, help="Mindestzahl Treffer, damit eine Kante aufgenommen wird")
    args = ap.parse_args()

    if not args.ordner.is_dir():
        print(f"Ordner nicht gefunden: {args.ordner}", file=sys.stderr)
        sys.exit(1)

    print(f"Lese XML aus {args.ordner} ...")
    kanten, gefunden = extrahiere(args.ordner)

    if not kanten:
        print("Keine Verweise gefunden. Pruefe DATEI_ZU_NORM und die Dateinamen.", file=sys.stderr)
        sys.exit(2)

    daten = baue_json(kanten, gefunden, args.min)
    args.out.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nFertig: {len(daten['nodes'])} Knoten, {len(daten['links'])} Kanten -> {args.out}")
    print("\nTop-Verbindungen:")
    for l in daten["links"][:12]:
        print(f"  {l['source']:>10} -> {l['target']:<10} {l['anzahl']:>4} Treffer")
    print("\nHinweis: Die Trefferzahl misst Zitierhaeufigkeit, nicht inhaltliches Gewicht.")
    print("Eine haeufig zitierte Begriffsnorm kann weniger relevant sein als ein einzelner,")
    print("aber zentraler Verweis. Vor Verwendung inhaltlich pruefen.")


if __name__ == "__main__":
    main()
