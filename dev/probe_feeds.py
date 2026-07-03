"""Temporäres Skript (Runde 2): findet echte Feed-URLs hinter HTML-Seiten.

Lädt Übersichts-/Presseseiten und extrahiert alle Links, die nach
RSS/Feed aussehen. Wird nach der Verifikation wieder entfernt.
"""

import re
import ssl
import urllib.request

import update_radar as ur

HTML_SEITEN = [
    ("ZfK RSS-Seite",   "https://www.zfk.de/rss-feed"),
    ("VKU RSS-Seite",   "https://www.vku.de/rss/"),
    ("VKU Presse-Feed", "https://www.vku.de/rss/rss-vku-pressemitteilungen/"),
    ("50Hertz News",    "https://www.50hertz.com/de/News"),
    ("Amprion Presse",  "https://www.amprion.net/Presse/"),
    ("TransnetBW",      "https://www.transnetbw.de/de/newsroom"),
    ("EU Energie News", "https://energy.ec.europa.eu/news_en"),
]

FEED_KANDIDATEN_2 = [
    ("ZfK alt+Accept",  "https://www.zfk.de/rss-feed"),
]


def hole_html(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  FEHLER {url}: {e}")
        return None


def main():
    print("=" * 70)
    for name, url in HTML_SEITEN:
        print(f"\n### {name}: {url}")
        html = hole_html(url)
        if html is None:
            continue
        # href- und link-Tags mit rss/feed/xml
        treffer = set(re.findall(
            r'(?:href|src)=["\']([^"\']*(?:rss|feed|atom)[^"\']*)["\']',
            html, re.IGNORECASE))
        treffer |= set(re.findall(
            r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']',
            html, re.IGNORECASE))
        for t in sorted(treffer)[:15]:
            print(f"  → {t}")
        if not treffer:
            print("  (keine Feed-Links gefunden)")
    print("=" * 70)


if __name__ == "__main__":
    main()
