import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
LAST_RUN_PATH = os.path.join(BASE_DIR, "last_run.json")
SKRIPT_PATH   = os.path.join(BASE_DIR, "update_radar.py")

# Laufender Update-Prozess (global, damit wir ihn prüfen können)
_laufender_prozess = None


class RadarHandler(BaseHTTPRequestHandler):

    def _sende_json(self, daten, status=200):
        body = json.dumps(daten, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",  "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

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
        # Alle anderen Routen → 404
        # ------------------------------------------------------------------
        else:
            self._sende_json({"fehler": "Route nicht gefunden"}, status=404)

    def log_message(self, fmt, *args):
        # Kompakteres Log-Format
        print(f"  {self.address_string()}  {fmt % args}")


def main():
    server = HTTPServer(("localhost", 5050), RadarHandler)
    print("Radar-Server läuft auf http://localhost:5050")
    print("  GET /status          → aktueller Status")
    print("  GET /starte-update   → startet update_radar.py")
    print("  Beenden mit Strg+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer wird beendet …")
        server.server_close()
        print("Server gestoppt.")


if __name__ == "__main__":
    main()
