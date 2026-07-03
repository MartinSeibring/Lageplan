"""Temporäres Skript (Runde 3): finale Kandidaten als Feed verifizieren."""

import update_radar as ur

KANDIDATEN = [
    ("VKU Meldungen", "https://www.vku.de/rss/rss-aktuelle-meldungen.xml?tx_wwt3list_recordlist%5Baction%5D=rss&tx_wwt3list_recordlist%5BcontentUid%5D=2563&tx_wwt3list_recordlist%5Bcontroller%5D=Recordlist&cHash=9823aefb7d917d08014286db8c6d7830"),
    ("VKU Presse",    "https://www.vku.de/rss/rss-vku-pressemitteilungen.xml?tx_wwt3list_recordlist%5Baction%5D=rss&tx_wwt3list_recordlist%5BcontentUid%5D=2564&tx_wwt3list_recordlist%5Bcontroller%5D=Recordlist&cHash=0d1cdca25109854d9c6eeba84c6d2110"),
    ("EU Energie",    "https://energy.ec.europa.eu/node/2/rss_en"),
    ("Google News",   "https://news.google.com/rss/search?q=Netzentgelt&hl=de&gl=DE&ceid=DE:de"),
]


def main():
    print("=" * 70)
    for name, url in KANDIDATEN:
        baum = ur.hole_feed(url)
        if baum is None:
            print(f"✗ {name}")
        else:
            items = ur.feed_items(baum)
            beispiel = items[0][0][:60] if items else "-"
            print(f"✓ {name}: {len(items)} Eintraege | Beispiel: {beispiel}")
    print("=" * 70)


if __name__ == "__main__":
    main()
