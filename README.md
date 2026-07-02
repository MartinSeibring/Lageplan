# Lageplan

Strategisches Cockpit für Energie & Asset Management — Themenradar,
Meilensteine & GANTT, Risikomanagement.

## Themenradar-Aktualisierung (läuft auf GitHub)

Die automatische Radar-Recherche läuft **komplett auf GitHub** — ein
lokaler Python-Server ist dafür nicht mehr nötig.

**Ablauf:**

1. `update_radar.py` liest `config.json` (Keywords + RSS-Feeds), ruft die
   Feeds ab und gleicht sie gegen die Keywords ab.
2. Ergebnisse landen im Repository:
   - `data/radar-vorschlaege.json` — die Themenvorschläge
   - `data/last_run.json` — Zeitstempel des letzten Laufs
   - `data/radar-gesehen.json` — Merkliste bereits vorgeschlagener Artikel
3. Die App lädt die Vorschläge über die GitHub-API und zeigt sie im
   Themenradar-Tab an („In Radar übernehmen" / „Ignorieren").

**Auslösung:**

- **Automatisch:** werktags ca. 06:30 Uhr (Workflow `update-radar.yml`,
  Zeitplan läuft auf dem Standard-Branch des Repos)
- **Manuell aus der App:** Button „Radar aktualisieren" im Themenradar-Tab
  startet den Workflow über die GitHub-API (dauert ca. 1–2 Minuten)
- **Manuell auf GitHub:** Actions → „Themenradar aktualisieren" → Run workflow

**Voraussetzung:** In der App muss unter *Einstellungen → GitHub-Sync* ein
Personal Access Token (PAT) hinterlegt sein — derselbe, der auch für die
Datensynchronisation genutzt wird. Der Token braucht Schreibrecht auf das
Repository (classic: Scope `repo`; fine-grained: *Contents* und *Actions*
Read/Write).

### Fehlerbehebung

| Anzeige | Ursache / Lösung |
|---|---|
| „GitHub-Token fehlt" | PAT unter Einstellungen → GitHub-Sync eintragen |
| „Start fehlgeschlagen: 404" | Workflow-Datei fehlt auf dem eingestellten Branch, oder PAT hat keine Actions-Berechtigung |
| „Start fehlgeschlagen: 422" | Der in den Sync-Einstellungen gewählte Branch existiert nicht |
| „Timeout" | Actions-Tab auf GitHub öffnen und Lauf-Protokoll prüfen |

## Lokaler Server (optional, nur für KI-Analyse)

`server.py` wird für die Radar-Aktualisierung **nicht mehr benötigt**.
Er bietet weiterhin optionale lokale Endpunkte für die KI-Dokumenten-Analyse
(`/ki-analyse`, `/fetch-url`) — dafür wird ein Anthropic-API-Key in
`config.json` benötigt (Feld `anthropic_api_key`).

Start: `start-server.bat` (Windows) bzw. `./start-server.sh` (Mac/Linux),
oder manuell:

```bash
pip install -r requirements.txt
python3 server.py
```
