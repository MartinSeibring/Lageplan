# Lageplan

Strategisches Cockpit für Energie & Asset Management — Themenradar,
Meilensteine & GANTT, Risikomanagement.

## Radar-Server starten (Python)

Die automatische Themenradar-Aktualisierung und die KI-Analyse benötigen
einen lokalen Python-Server (`server.py`, Port 5050). Zeigt die Seite
**„⚠ Server nicht aktiv"**, läuft dieser Server gerade nicht.

### Schnellstart

**Windows:** Doppelklick auf `start-server.bat`

**Mac/Linux:**
```bash
./start-server.sh
```
(einmalig ausführbar machen: `chmod +x start-server.sh`)

Die Skripte installieren fehlende Python-Pakete automatisch und starten
den Server. Das Fenster muss offen bleiben, solange der Lageplan genutzt
wird. Die Seite erkennt den Server automatisch innerhalb von ~10 Sekunden.

### Manueller Start

```bash
pip install -r requirements.txt
python3 server.py
```

Erwartete Ausgabe: `Radar-Server läuft auf http://localhost:5050`

### Fehlerbehebung „Server nicht aktiv"

| Prüfung | Lösung |
|---|---|
| Läuft `server.py` in einem Terminal? | Falls nein: Start-Skript ausführen (s. o.) |
| Python installiert? (`python3 --version`) | Von [python.org](https://www.python.org/downloads/) installieren |
| Pakete installiert? | `pip install -r requirements.txt` |
| Port 5050 belegt? | Anderes Programm auf Port 5050 beenden |
| Meldung „update_radar.py nicht gefunden"? | Das Skript `update_radar.py` muss im gleichen Ordner wie `server.py` liegen (nicht im Repo enthalten) |

### Hinweis zu `update_radar.py`

`server.py` startet beim Klick auf „Radar aktualisieren" das Skript
`update_radar.py`. Diese Datei ist **nicht** im Repository enthalten und
muss lokal neben `server.py` liegen. Fehlt sie, zeigt die Seite jetzt
eine entsprechende Fehlermeldung an.

### KI-Analyse (optional)

Für die KI-Funktionen (URL-/PDF-Analyse) wird ein Anthropic-API-Key in
`config.json` benötigt (Feld `anthropic_api_key`).
