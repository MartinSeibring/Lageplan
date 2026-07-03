"""Temporäres Skript: testet RSS-Kandidaten-URLs auf dem GitHub-Runner.

Nutzt dieselbe Abruflogik wie update_radar.py und meldet pro URL,
ob sie ein parsebarer Feed ist und wie viele Einträge sie liefert.
Wird nach der Verifikation wieder entfernt.
"""

import update_radar as ur

KANDIDATEN = [
    ("ZfK a",        "https://www.zfk.de/rss.xml"),
    ("ZfK b",        "https://www.zfk.de/feed"),
    ("ZfK c",        "https://www.zfk.de/rss/news"),
    ("ZfK d",        "https://www.zfk.de/rss-feed"),
    ("pv-magazine",  "https://www.pv-magazine.de/feed/"),
    ("CLEW a",       "https://www.cleanenergywire.org/rss"),
    ("CLEW b",       "https://www.cleanenergywire.org/rss.xml"),
    ("energate a",   "https://www.energate-messenger.de/rss"),
    ("energate b",   "https://www.energate-messenger.de/feed/"),
    ("BDEW a",       "https://www.bdew.de/rss/"),
    ("BDEW b",       "https://www.bdew.de/feed/"),
    ("BDEW c",       "https://www.bdew.de/presse/presseinformationen/feed/"),
    ("VKU Meldungen","https://www.vku.de/rss/rss-aktuelle-meldungen/"),
    ("VKU Presse",   "https://www.vku.de/rss/rss-vku-pressemitteilungen/"),
    ("50Hertz a",    "https://www.50hertz.com/de/rss"),
    ("50Hertz b",    "https://www.50hertz.com/rss"),
    ("Amprion a",    "https://www.amprion.net/rss.xml"),
    ("Amprion b",    "https://www.amprion.net/Presse/rss.xml"),
    ("TenneT a",     "https://www.tennet.eu/de/rss"),
    ("TenneT b",     "https://www.tennet.eu/rss.xml"),
    ("TransnetBW a", "https://www.transnetbw.de/de/rss"),
    ("TransnetBW b", "https://www.transnetbw.de/rss.xml"),
    ("BMUV a",       "https://www.bundesumweltministerium.de/meldungen.rss"),
    ("BMUV b",       "https://www.bmuv.de/meldungen.rss"),
    ("EU ENER a",    "https://ec.europa.eu/newsroom/ener/items/itemType/1047/rss"),
    ("EU ENER b",    "https://ec.europa.eu/newsroom/ener/rss.cfm"),
    ("EU ENER c",    "https://energy.ec.europa.eu/rss.xml"),
    ("EU ENER d",    "https://energy.ec.europa.eu/news_en.rss"),
]


def main():
    print("=" * 70)
    for name, url in KANDIDATEN:
        baum = ur.hole_feed(url)
        if baum is None:
            print(f"✗ {name:15s} {url}")
        else:
            items = ur.feed_items(baum)
            beispiel = items[0][0][:50] if items else "-"
            print(f"✓ {name:15s} {len(items):3d} Eintraege | {url}")
            print(f"    Beispiel: {beispiel}")
    print("=" * 70)


if __name__ == "__main__":
    main()
