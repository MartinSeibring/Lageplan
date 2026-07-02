#!/bin/bash
# ── Radar-Server starten (Mac/Linux) ───────────────────────
# Ausführen mit:  ./start-server.sh
# (einmalig ausführbar machen: chmod +x start-server.sh)
# Fenster offen lassen, solange der Lageplan genutzt wird.

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "FEHLER: python3 ist nicht installiert."
  echo "Mac:   brew install python3   (oder von python.org)"
  echo "Linux: sudo apt install python3 python3-pip"
  exit 1
fi

echo "Prüfe/installiere Python-Pakete ..."
python3 -m pip install -q -r requirements.txt

echo ""
echo "Starte Radar-Server auf http://localhost:5050 ..."
echo "(Dieses Fenster offen lassen! Beenden mit Strg+C)"
echo ""
python3 server.py
