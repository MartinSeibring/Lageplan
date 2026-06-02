import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from bs4 import BeautifulSoup

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
LAST_RUN_PATH = os.path.join(BASE_DIR, "last_run.json")
SKRIPT_PATH   = os.path.join(BASE_DIR, "update_radar.py")
CONFIG_PATH   = os.path.join(BASE_DIR, "config.json")

# Laufender Update-Prozess (global, damit wir ihn prüfen können)
_laufender_prozess = None


class RadarHandler(BaseHTTPRequestHandler):

    def _sende_json(self, daten, status=200):
        body = json.dumps(daten, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",  "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        global _laufender_prozess

        # ------------------------------------------------------------------
        # GET /status
        # ------------------------------------------------------------------
        if self.path == "/status":
            letzter_lauf = None
            if os.path.exists(LAST_RUN_PATH):
                try:
                    with open(LAST_RUN_PATH, encoding="utf-8") as f:
                        letzter_lauf = json.load(f)
                except (json.JSONDecodeError, OSError):
                    letzter_lauf = None

            laeuft = (_laufender_prozess is not None and
                      _laufender_prozess.poll() is None)

            self._sende_json({
                "status":       "laeuft" if laeuft else "bereit",
                "letzter_lauf": letzter_lauf,
            })

        # ------------------------------------------------------------------
        # GET /starte-update
        # ------------------------------------------------------------------
        elif self.path == "/starte-update":
            if _laufender_prozess is not None and _laufender_prozess.poll() is None:
                self._sende_json({"status": "laeuft-bereits"})
            else:
                _laufender_prozess = subprocess.Popen(
                    ["python3", SKRIPT_PATH],
                    cwd=BASE_DIR,
                )
                self._sende_json({"status": "gestartet"})

        # ------------------------------------------------------------------
        # GET /vorschlaege
        # ------------------------------------------------------------------
        elif self.path == "/vorschlaege":
            vorschlaege_dir = os.path.join(BASE_DIR, "vorschlaege")
            if not os.path.exists(vorschlaege_dir):
                self._sende_json({"vorschlaege": [], "hinweis": "Noch keine Vorschläge"})
                return

            dateien = sorted(
                [f for f in os.listdir(vorschlaege_dir)
                 if f.startswith("vorschlaege-") and f.endswith(".json")],
                reverse=True   # neueste zuerst (ISO-Datum im Namen)
            )

            if not dateien:
                self._sende_json({"vorschlaege": [], "hinweis": "Noch keine Vorschläge"})
                return

            neueste = os.path.join(vorschlaege_dir, dateien[0])
            try:
                with open(neueste, encoding="utf-8") as f:
                    inhalt = json.load(f)
                self._sende_json(inhalt)
            except (json.JSONDecodeError, OSError) as e:
                self._sende_json({"vorschlaege": [], "hinweis": f"Lesefehler: {e}"})

        # ------------------------------------------------------------------
        # GET /config
        # ------------------------------------------------------------------
        elif self.path == "/config":
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    config = json.load(f)
                self._sende_json(config)
            except (json.JSONDecodeError, OSError) as e:
                self._sende_json({"fehler": f"config.json nicht lesbar: {e}"}, status=500)

        # ------------------------------------------------------------------
        # Alle anderen Routen → 404
        # ------------------------------------------------------------------
        else:
            self._sende_json({"fehler": "Route nicht gefunden"}, status=404)

    def do_POST(self):
        # ------------------------------------------------------------------
        # POST /config
        # ------------------------------------------------------------------
        if self.path == "/config":
            laenge = int(self.headers.get("Content-Length", 0))
            try:
                body = self.rfile.read(laenge)
                daten = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self._sende_json({"fehler": f"Ungültiges JSON: {e}"}, status=400)
                return

            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError):
                config = {}

            if "keywords" in daten:
                config["keywords"] = daten["keywords"]
            if "feeds" in daten:
                config["rss_feeds"] = [
                    {"name": fd.get("name", ""), "url": fd.get("url", ""), "aktiv": fd.get("aktiv", True)}
                    for fd in daten["feeds"]
                ]
            if "quellen" in daten:
                config["behoerden_seiten"] = [
                    {"name": q.get("name", ""), "url": q.get("url", ""),
                     "selektor": q.get("selektor", "body"), "aktiv": q.get("aktiv", True)}
                    for q in daten["quellen"]
                ]

            try:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except OSError as e:
                self._sende_json({"fehler": f"Schreibfehler: {e}"}, status=500)
                return

            n_kw  = len(daten.get("keywords", []))
            n_fd  = len(daten.get("feeds",    []))
            n_qu  = len(daten.get("quellen",  []))
            print(f"  Konfiguration aktualisiert: {n_kw} Keywords, {n_fd} Feeds, {n_qu} Quellen")
            self._sende_json({"status": "gespeichert"})

        # ------------------------------------------------------------------
        # POST /fetch-url
        # ------------------------------------------------------------------
        elif self.path == "/fetch-url":
            laenge = int(self.headers.get("Content-Length", 0))
            try:
                body = self.rfile.read(laenge)
                daten = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self._sende_json({"error": f"Ungültiges JSON: {e}"}, status=400)
                return

            url = (daten.get("url") or "").strip()
            if not re.match(r"^https?://", url, re.IGNORECASE):
                self._sende_json({"error": "URL muss mit http:// oder https:// beginnen."}, status=400)
                return

            try:
                resp = requests.get(
                    url, timeout=20,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
            except requests.exceptions.Timeout:
                self._sende_json({"error": "Zeitüberschreitung beim Abrufen der URL."}, status=504)
                return
            except requests.exceptions.RequestException as e:
                self._sende_json({"error": f"Abruf fehlgeschlagen: {e}"}, status=502)
                return

            soup = BeautifulSoup(resp.text, "html.parser")

            for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            titel = soup.title.get_text(strip=True) if soup.title else ""

            rohtext = soup.get_text(separator="\n")
            zeilen  = [z.strip() for z in rohtext.splitlines()]
            # Mehrfache Leerzeilen auf eine reduzieren
            bereinigt_zeilen = []
            leerzeile_davor  = False
            for z in zeilen:
                if z:
                    bereinigt_zeilen.append(z)
                    leerzeile_davor = False
                elif not leerzeile_davor:
                    bereinigt_zeilen.append("")
                    leerzeile_davor = True

            text   = "\n".join(bereinigt_zeilen).strip()
            text   = text[:50_000]
            zeichen = len(text)

            print(f"  URL abgerufen: {url} – {zeichen} Zeichen")
            self._sende_json({"text": text, "titel": titel, "zeichen": zeichen})

        else:
            self._sende_json({"fehler": "Route nicht gefunden"}, status=404)

    def log_message(self, fmt, *args):
        # Kompakteres Log-Format
        print(f"  {self.address_string()}  {fmt % args}")


def main():
    server = HTTPServer(("localhost", 5050), RadarHandler)
    print("Radar-Server läuft auf http://localhost:5050")
    print("  GET  /status         → aktueller Status")
    print("  GET  /starte-update  → startet update_radar.py")
    print("  GET  /config         → liefert config.json")
    print("  POST /config         → speichert config.json")
    print("  POST /fetch-url      → ruft URL ab und liefert Volltext")
    print("  Beenden mit Strg+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer wird beendet …")
        server.server_close()
        print("Server gestoppt.")


if __name__ == "__main__":
    main()
