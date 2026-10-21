# Lageplan

Strategisches Cockpit für Energie & Asset Management — Themenradar,
Meilensteine & GANTT, Risikomanagement.

## Themenradar-Aktualisierung (läuft auf GitHub)

Die automatische Radar-Recherche läuft **komplett auf GitHub** — ein
lokaler Python-Server ist dafür nicht mehr nötig.

**Ablauf:**

1. Der Workflow checkt zusätzlich das private Daten-Repo
   `martinseibring/lageplan-daten` aus. `update_radar.py` liest
   `produktiv/config.json` (Keywords + RSS-Feeds), ruft die Feeds ab und
   gleicht sie gegen die Keywords ab.
2. Ergebnisse landen **immer** im Ordner `produktiv/` des Daten-Repos:
   - `radar-vorschlaege.json` — die Themenvorschläge
   - `last_run.json` — Zeitstempel des letzten Laufs
   - `radar-gesehen.json` — Merkliste bereits vorgeschlagener Artikel
3. Die App lädt die Vorschläge über die GitHub-API und zeigt sie im
   Themenradar-Tab an („In Radar übernehmen" / „Ignorieren"). Alle
   Umgebungen lesen die Radar-Dateien aus `produktiv/`.

Schlägt der Push ins Daten-Repo fehl, wird der Lauf **rot** (früher wurde
der Fehler verschluckt).

**Auslösung:**

- **Automatisch:** werktags ca. 06:30 Uhr (Workflow `update-radar.yml`,
  Zeitplan läuft auf dem Standard-Branch des Repos)
- **Manuell aus der App:** Button „Radar aktualisieren" im Themenradar-Tab
  startet den Workflow über die GitHub-API (dauert ca. 1–2 Minuten)
- **Manuell auf GitHub:** Actions → „Themenradar aktualisieren" → Run workflow

**Voraussetzungen:**

- Repository-Secret `DATEN_TOKEN` im Code-Repo: fine-grained PAT mit
  *Contents: Read/Write* auf `lageplan-daten` (nutzt der Workflow).
- In der App unter *Einstellungen → GitHub-Sync* ein PAT mit
  *Contents: Read/Write* auf `lageplan-daten` und *Actions: Read/Write* auf
  `lageplan` (classic: Scope `repo`).

## Branches und Datenablage

| Branch | Zweck | Seite |
|---|---|---|
| `development` | neue Entwicklungen | `/dev/` |
| `staging` | Test | `/staging/` |
| `Produktiv` | Regelbetrieb (geschützt, nur per Pull Request) | `/` |
| `gh-pages` | technisch: Ziel von `deploy.yml`, nicht anfassen | – |

Code wandert `development` → `staging` → `Produktiv`. Die Daten liegen
**nicht** im Code-Repo, sondern im privaten Repo `lageplan-daten`
(Ordner `produktiv/`, `staging/`, `development/`) – Merges zwischen den
Branches erzeugen deshalb keine Datenkonflikte mehr.

### Fehlerbehebung

| Anzeige | Ursache / Lösung |
|---|---|
| „GitHub-Token fehlt" | PAT unter Einstellungen → GitHub-Sync eintragen |
| „Start fehlgeschlagen: 404" | PAT hat keine Actions-Berechtigung auf `lageplan` |
| Lauf rot bei „Checkout Daten-Repo“ / „Ergebnisse committen“ | Secret `DATEN_TOKEN` fehlt, ist abgelaufen oder hat kein Schreibrecht auf `lageplan-daten` |
| „Timeout" | Actions-Tab auf GitHub öffnen und Lauf-Protokoll prüfen |

## Lokaler Server (optional, nur für KI-Analyse)

`server.py` wird für die Radar-Aktualisierung **nicht mehr benötigt**.
Er bietet weiterhin optionale lokale Endpunkte für die KI-Dokumenten-Analyse
(`/ki-analyse`, `/fetch-url`) — dafür wird ein Anthropic-API-Key benötigt.

> ⚠ **Den API-Key NIEMALS in `config.json` eintragen** — die Datei liegt im
> öffentlichen Repository und wird mit veröffentlicht. Stattdessen als
> Umgebungsvariable setzen, bevor der Server gestartet wird:
> `set ANTHROPIC_API_KEY=sk-…` (Windows) bzw.
> `export ANTHROPIC_API_KEY=sk-…` (Mac/Linux).

Start: `start-server.bat` (Windows) bzw. `./start-server.sh` (Mac/Linux),
oder manuell:

```bash
pip install -r requirements.txt
python3 server.py
```
