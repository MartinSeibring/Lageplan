#!/usr/bin/env python3
"""Erzeugt swm/lageplan.html (Standalone) aus index.html.

Aufruf (im Repo-Hauptordner):
    npm pack d3@7.8.5   # liefert d3-7.8.5.tgz, darin package/dist/d3.min.js
    python3 -I swm/werkzeug/erzeuge-lageplan.py index.html <pfad>/d3.min.js swm/lageplan.html

Jede Änderung prüft, dass ihre Fundstelle eindeutig ist; ändert sich
index.html an einer betroffenen Stelle, bricht das Skript mit Hinweis ab.
"""
import sys, pathlib

SRC, D3, DST = sys.argv[1], sys.argv[2], sys.argv[3]
lines = pathlib.Path(SRC).read_text(encoding="utf-8").split("\n")


def find(pat, start=0, exact=False, unique=True):
    hits = [i for i in range(start, len(lines))
            if (lines[i] == pat if exact else pat in lines[i])]
    if not hits:
        sys.exit(f"NICHT GEFUNDEN: {pat!r}")
    if unique and len(hits) > 1 and start == 0:
        sys.exit(f"MEHRDEUTIG ({len(hits)}): {pat!r} -> {hits[:5]}")
    return hits[0]


def cut(start_pat, end_pat, start_off=0, end_incl=False, end_exact=False):
    """Löscht Zeilen von start (inkl.) bis end (exkl., bzw. inkl.)."""
    global lines
    s = find(start_pat) + start_off
    e = find(end_pat, start=s + 1, exact=end_exact, unique=False)
    if end_incl:
        e += 1
    del lines[s:e]
    return e - s


def cut_line(pat, unique=True):
    global lines
    del lines[find(pat, unique=unique)]


def text_rep(old, new, count=1):
    global lines
    t = "\n".join(lines)
    n = t.count(old)
    if n != count:
        sys.exit(f"ERSETZEN: {n}x statt {count}x gefunden: {old[:80]!r}")
    lines = t.replace(old, new).split("\n")


# ───────────────────────────── HEAD ─────────────────────────────
d3src = pathlib.Path(D3).read_text(encoding="utf-8")
i = find('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>')
lines[i] = "  <script>/* d3 v7.8.5 (ISC License, https://d3js.org) – eingebettet für Offline-Betrieb */\n" + d3src.strip() + "\n</script>"
cut_line('<link rel="preconnect" href="https://fonts.googleapis.com">')
cut_line('href="https://fonts.googleapis.com/css2?family=Open+Sans')

# ───────────────────────────── CSS ──────────────────────────────
cut("#st-header {", "/* ── Bestätigungs-Banner", start_off=-1)
cut_line("#tab-max       {")
cut_line("#tab-max:hover {")
cut("/* ── GitHub Sync ── */", "/* ── Dokument-Analyse Modal ── */")
cut("/* ── Dokument-Analyse Modal ── */", "/* ── Forschungsprojekte ── */")
# FP-CSS bleibt: das Risiko-Formular/-Detail nutzt die Klassen fp-form-*/fp-detail-*
for b in ("projekte", "betrieb", "risiko"):
    for _ in range(2):
        cut_line(f'    .lp-kachel[data-bereich="{b}"]', unique=False)
text_rep("grid-template-rows: auto auto minmax(180px, auto) minmax(140px, auto);",
         "grid-template-rows: minmax(260px, auto) minmax(260px, auto);")
text_rep('.lp-kachel[data-bereich="horizont"]     { grid-column: 1/3; grid-row: 1/5; }',
         '.lp-kachel[data-bereich="horizont"]     { grid-column: 1/3; grid-row: 1/3; }')
text_rep("Rechts (col 3-4): Meilensteine, Ziele, Projekte+Betrieb, Risiko gestapelt.",
         "Rechts (col 3-4): Meilensteine und Ziele gestapelt.")
text_rep("/* Grid: 4 Spalten, 4 Zeilen.\n       Horizont belegt links col 1-2 über alle 4 Zeilen",
         "/* Grid: 4 Spalten, 2 Zeilen.\n       Horizont belegt links col 1-2 über beide Zeilen")

# ───────────────────────────── HTML ─────────────────────────────
cut_line('<button id="app-hilfe-btn"')
cut_line('<button class="app-tab" id="tab-max"')
cut_line('<button class="app-tab" id="tab-settings"')
# Statusleiste: "Keywords aktiv"
k = find('id="ampel-keywords"')
assert "status-trennlinie" in lines[k - 3] and "</div>" in lines[k + 3], lines[k-3:k+4]
del lines[k - 3:k + 4]
# Kacheln 4–6 (bis zum schließenden </div> des Rasters)
cut("<!-- ── Kachel 4: Forschungsprojekte", "    </div>", end_exact=True)
# Forschungsprojekte-Panels/Modals bis zum Ende des Lageplan-Panels
cut("<!-- ── Forschungsprojekte Detail-Panel", "</div>", end_exact=True)
# Themenradar-Kopf: "Daten exportieren (JSON)" (ersetzt durch Gesamt-Export) + "Radar aktualisieren"
i = find('onclick="TR.exportiereJSON()">Daten exportieren (JSON)</button>')
del lines[i - 1:i + 1]
i = find('onclick="TR.starteAktualisierung()">Radar aktualisieren</button>')
del lines[i - 1:i + 1]
cut_line('<span id="update-status"')
# Dokument-Kasten im Thema-Formular
i = find('<div style="margin:0 0 12px;padding:10px 12px;background:#f0f7fa')
assert lines[i + 7].strip() == "</div>", lines[i + 7]
del lines[i:i + 8]
cut("<!-- ── Themenradar: Dokument-Analyse Modal", '<div id="hinweis"')
# KI-Modal: nur „JSON einfügen" bleibt
cut("<!-- Tab-Leiste -->", "<!-- Tab 0: JSON einfügen")
cut("<!-- Tab 1: URL -->", "<!-- Verknüpftes Thema (nur JSON-Tab) -->")
i = find("<!-- Fortschrittsanzeige (URL + PDF) -->")
assert lines[i + 4].strip() == "</div>", lines[i + 4]
del lines[i:i + 6]
# Meilensteine-Kopf
cut_line('<span id="gh-sync-pill"')
cut_line('<button id="btn-ms-export"')
cut("<!-- ── GitHub Sync Einstellungen", "<!-- ── Meilenstein-Formular")
# Einstellungen-Panel
cut('<div class="tab-panel" id="panel-settings">', "<script>/* ===== Lokaler Speicher je Umgebung")
# Handbuch
cut("<!-- ── Handbuch-Modal", "</body>")

# ────────────────────────── JS: Speicher ─────────────────────────
s = find("<script>/* ===== Lokaler Speicher je Umgebung ===== */")
e = find("</script>", start=s, unique=False)
lines[s:e + 1] = """<script>/* ===== Lokaler Zwischenspeicher ===== */
// Standalone-Version: Daten liegen im localStorage des Browsers (nur
// Zwischenspeicher) und werden über „Daten exportieren / importieren"
// als JSON-Datei gesichert. Eigenes Präfix, damit sich die Daten nicht mit
// der Web-Version mischen.
window.lsKey = function(name) { return "lageplan-html:" + name; };
</script>""".split("\n")

# ────────────────────────── JS: Themenradar ──────────────────────
cut("// Update-Vorschlag an bestehendes Thema anhängen (Verlauf)",
    "    function uebernehmeVorschlag(", )
s = find("    // Radar-Aktualisierung über GitHub Actions") - 1
e = find("    // ── HTML-Escaping für Inhalte aus externen Feeds", start=s, unique=False)
del lines[s:e]
s = find("    // Offene Vorschläge aus dem Repo laden")
e = find("    // Meilenstein-Verbindung (localStorage)", start=s, unique=False) - 1
del lines[s:e]
cut_line("    pruefeServerStatus();")
text_rep("""      // Bearbeitete Themen direkt nach GitHub schreiben – der Standard-Sync
      // uebertraegt nur NEUE Themen, Aenderungen an bestehenden gingen verloren
      if (warBearbeitung && gespeichert && window.GH && GH.schreibeThemaDirekt) {
        try { GH.schreibeThemaDirekt(gespeichert); } catch(e) {}
      }

""", "")
# Laden aus Datei (Import) statt GitHub
s = find("    // ── GitHub-Daten laden (ersetzt lokale manuell_erfasst-Einträge) ──")
e = find("    // ── Manuell erfasste Themen in localStorage sichern ──", start=s, unique=False)
lines[s:e] = """    // ── Themen aus Import-Datei übernehmen (ersetzt den gesamten Bestand) ──
    function ladeDaten(daten) {
      if (!Array.isArray(daten)) return;
      radarData.length = 0;
      daten.forEach(function(d) {
        if (!d || d.id === undefined || d.id === null) return;
        d.radar_score = berechneScore(d);
        radarData.push(d);
      });
      speichereManuelleThemen();
      zeichnePunkte();
    }

""".split("\n")
s = find("    // ── Manuell erfasste Themen in localStorage sichern ──")
e = find("    // ── Mini-Zielscheibe für Lageplan-Kachel", start=s, unique=False)
lines[s:e] = """    // ── Alle Themen im Zwischenspeicher sichern ──
    // (Standalone: auch geänderte/gelöschte Standard-Themen, da es keinen
    //  Server-Abgleich mehr gibt.)
    function speichereManuelleThemen() {
      try {
        localStorage.setItem(lsKey("themen"), JSON.stringify(radarData));
      } catch (e) { /* Storage voll – ignorieren */ }
      aktualisiereManuellCounter();
    }

    // ── Beim Seitenstart: gespeicherten Themenbestand laden ──
    function ladeManuellErfassteThemen() {
      try {
        const raw = localStorage.getItem(lsKey("themen"));
        if (raw) {
          const gespeichert = JSON.parse(raw);
          if (Array.isArray(gespeichert)) {
            radarData.length = 0;
            gespeichert.forEach(d => {
              if (!d || d.id === undefined || d.id === null) return;
              d.radar_score = berechneScore(d);
              radarData.push(d);
            });
          }
        }
      } catch (e) { /* ignorieren */ }
      aktualisiereManuellCounter();
    }

""".split("\n")
# KI: nur JSON-Pfad, keine Server-Aufrufe
s = find("      // ── Pfad B: Server-Analyse (URL / PDF) ──")
e = find("    function zeigeKiVorschlaege(vorschlaege, thema) {", start=s, unique=False)
lines[s:e] = ["    }", ""]
text_rep("""      // ── Pfad A: JSON direkt einfügen (kein Server nötig) ──
      if (_kiAktuellerTab === "json") {""", """      // JSON-Antwort direkt einfügen (kein Server nötig)
      {""")
s = find("    function _kiSetzeUrl(url) {")
e = find("    function _kiValidiereEingabe() {", start=s, unique=False)
del lines[s:e]
s = find("    function _kiDateiAusgewaehlt(file) {")
e = find("    function oeffneKiModal(themaId) {", start=s, unique=False)
del lines[s:e]
# Dokument-Analyse (Server) komplett
s = find("    // ── Dokument-Analyse ─────")
e = find("window.TR={", start=s, unique=False)
del lines[s:e]
i = find("window.TR={")
lines[i] = ("window.TR={setzeAnsicht,sortiereListe,oeffneThemaFormular,exportiereJSON,ladeVorschlaege,"
            "schliesseThemaFormular,aktualisiereScore,aktualisiereSlider,speichereThema,schliesseLoeschenModal,"
            "filterAktualisieren,zeigeDetail,oeffneKiModal,schliesseKiModal,_kiWechsleTab,_kiKopierePrompt,"
            "starteKiAnalyse,ladeDaten,redraw:zeichnePunkte,renderMini:renderMini,"
            "getDaten:function(){ return radarData; }};")

# ────────────────────────── JS: Meilensteine ─────────────────────
text_rep("""        <h3>Kategorie</h3>
        ${["regulatorisch","marktlich","technologisch","wettbewerblich"].map(k => `
          <label class="ms-filter-zeile">
            <input type="checkbox" data-gruppe="kategorie" value="${k}" checked>
            <span class="ms-filter-punkt" style="background:${katFarben[k]}"></span>
            ${k.charAt(0).toUpperCase() + k.slice(1)}
          </label>
        `).join("")}

""", "")
text_rep("""      // Kategorie
      panel.querySelectorAll("input[data-gruppe='kategorie']").forEach(cb => {
        cb.addEventListener("change", function() {
          if (this.checked) filterState.kategorien.add(this.value);
          else              filterState.kategorien.delete(this.value);
          wendeFilterAn();
        });
      });

""", "")
text_rep('      kategorien:    new Set(["regulatorisch","marktlich","technologisch","wettbewerblich"]),\n', "")
text_rep('        filterState.kategorien    = new Set(["regulatorisch","marktlich","technologisch","wettbewerblich"]);\n', "")
text_rep("          const katOk  = filterState.kategorien.has(ms.kategorie);\n", "")
text_rep("_aktiv: clusterOk && katOk && statOk && suchtextOk", "_aktiv: clusterOk && statOk && suchtextOk")
text_rep("${(ms.manuell_erfasst === true || (window.GH && GH.ladeEinstellungen && GH.ladeEinstellungen().pat))\n"
         "            ? `<button id=\"btn-detail-loeschen\">🗑 Löschen</button>`\n"
         "            : \"\"}",
         "<button id=\"btn-detail-loeschen\">🗑 Löschen</button>")
text_rep("      if (window.GH && GH.debouncedSync) { try { GH.debouncedSync(); } catch(e) {} }\n", "")
text_rep("      if (window.GH && GH.debouncedSync) GH.debouncedSync();\n", "", count=2)
text_rep("""    function ladeVonGithub(daten) {
      if (!Array.isArray(daten)) return;
      // Leere GitHub-Datei niemals lokale Daten überschreiben lassen
      if (daten.length === 0 && meilensteinData.length > 0) return;
      meilensteinData.length = 0;""", """    // Meilensteine aus Import-Datei übernehmen (ersetzt den gesamten Bestand)
    function ladeDaten(daten) {
      if (!Array.isArray(daten)) return;
      meilensteinData.length = 0;""")
text_rep("    function ladeZieleVonGithub(daten) {", "    function ladeZiele(daten) {")
# Start: gespeicherten Gesamtbestand laden (nicht nur neue IDs)
text_rep("""      if (!Array.isArray(gespeichert) || gespeichert.length === 0) return;

      const vorhandeneIds = new Set(meilensteinData.map(m => m.id));
      const neu = gespeichert.filter(m => m.id && !vorhandeneIds.has(m.id));
      neu.forEach(m => {
        m.abhaengig_von = normAbh(m.abhaengig_von);  // Alt-Format vereinheitlichen
        meilensteinData.push(m);
      });
""", """      if (!Array.isArray(gespeichert)) return;

      // Standalone: der Zwischenspeicher enthält den vollständigen Bestand
      // (inkl. Änderungen/Löschungen an Standard-Meilensteinen).
      const bekannteIds = new Set(
        JSON.parse(localStorage.getItem(lsKey("meilensteine-bekannt")) || "[]"));
      const neu = gespeichert.filter(m => m.id && bekannteIds.size && !bekannteIds.has(m.id));
      meilensteinData.length = 0;
      gespeichert.forEach(m => {
        if (!m || !m.id) return;
        m.abhaengig_von = normAbh(m.abhaengig_von);  // Alt-Format vereinheitlichen
        meilensteinData.push(m);
      });
""")
text_rep("""    ladeAusLocalStorage();
    // Ziele aus localStorage laden""", """    ladeAusLocalStorage();
    // Erststart: Standardbestand in den Zwischenspeicher schreiben, damit
    // Ableitungen aus dem Themenradar ihn nicht überschreiben.
    try {
      if (!localStorage.getItem(lsKey("meilensteine")))
        localStorage.setItem(lsKey("meilensteine"), JSON.stringify(meilensteinData));
      localStorage.setItem(lsKey("meilensteine-bekannt"),
        JSON.stringify(meilensteinData.map(m => m.id)));
    } catch (e) {}
    // Ziele aus localStorage laden""")
# Bugfix: zielenData wird beim Start (weiter oben) bereits aus dem
# Zwischenspeicher befüllt; die spätere Deklaration darf sie nicht leeren.
text_rep("    var zielenData = [];",
         "    var zielenData = zielenData || [];  // bereits beim Start aus dem Zwischenspeicher befüllt (Hoisting)")
text_rep("if (Array.isArray(gz)) gz.forEach(function(z){ zielenData.push(z); });",
         "if (Array.isArray(gz)) { zielenData = zielenData || []; gz.forEach(function(z){ zielenData.push(z); }); }")
i = find("window.MS={exportiereJSON,")
lines[i] = (lines[i].replace("ladeVonGithub,ladeZieleVonGithub,", "ladeDaten,ladeZiele,"))
assert "ladeDaten,ladeZiele," in lines[i]

# ────────────────────────── JS: Module entfernen ─────────────────
cut("<script>/* ===== GitHub Sync ===== */", "</script>", end_incl=True, end_exact=True)
cut("<script>/* ===== Forschungsprojekte ===== */", "</script>", end_incl=True, end_exact=True)
cut("<script>/* ===== Einstellungen ===== */", "</script>", end_incl=True, end_exact=True)
cut("  <script>/* ===== Umgebungs-Banner ===== */", "</script>", end_incl=True)

# ────────────────────────── JS: Risikomanagement ─────────────────
text_rep("    if (window.GH && GH.debouncedRisikenSync) GH.debouncedRisikenSync();\n", "")
text_rep("""  function ladeVonGithub(daten) {
    risikenDaten.length = 0;""", """  // Risiken aus Import-Datei übernehmen (ersetzt den gesamten Bestand)
  function ladeDaten(daten) {
    if (!Array.isArray(daten)) return;
    risikenDaten.length = 0;""")
text_rep("    ladeVonGithub, renderTab, renderKachel, zeigeDetail, schliesseDetail,",
         "    ladeDaten, renderTab, renderKachel, zeigeDetail, schliesseDetail,")
text_rep("""    getDaten:   function(){ return risikenDaten; },
    getManuell: function(){ return risikenDaten.filter(function(r){ return r.manuell_erfasst; }); }""",
         """    getDaten:   function(){ return risikenDaten; }""")

# ────────────────────────── JS: Lageplan / App ───────────────────
text_rep("""      // Keywords
      let kwAnzahl = 0;
      try {
        const raw = localStorage.getItem("config-keywords");
        const kw  = raw ? JSON.parse(raw) : [];
        if (Array.isArray(kw)) kwAnzahl = kw.length;
      } catch(e) {}
      const wk = document.getElementById("wert-keywords");
      if (wk) wk.textContent = kwAnzahl || 12;
      if (window.FP && FP.renderKachel)       { try { FP.renderKachel();       } catch(e) {} }
""", "")
text_rep('  var PANELS = ["lageplan","themenradar","meilensteine","risiko","normennetz","settings"];',
         '  var PANELS = ["lageplan","themenradar","meilensteine","risiko","normennetz"];')
text_rep("""    normennetz:   "Normennetz | Energie & Asset Management",
    settings:     "Einstellungen | Energie & Asset Management"
""", """    normennetz:   "Normennetz | Energie & Asset Management"
""")
text_rep("      if (window.FP && FP.renderKachel) { try { FP.renderKachel(); } catch(e){} }\n", "")
text_rep("""  // GitHub Sync: Nach kurzem Delay laden, damit alle IIFEs initialisiert sind
  setTimeout(function() { if (window.GH) { GH.ladeMeilensteine(); GH.ladeThemen(); GH.ladeForschung(); GH.ladeRisiken(); } }, 500);
""", "")

# ────────────────────────── Neu: Export/Import ───────────────────
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from datei_snippets import BUTTONS, CSS, MODUL
i = find('<button class="app-tab" id="tab-normennetz"')
lines[i + 1:i + 1] = BUTTONS.split("\n")
i = find(".app-tab.aktiv { color: #fff; border-bottom-color: #fff; }")
lines[i + 1:i + 1] = CSS.split("\n")
i = find("<script>/* ===== App-Controller / Tab-Navigation ===== */")
lines[i:i] = MODUL.split("\n")

pathlib.Path(DST).write_text("\n".join(lines), encoding="utf-8")
print("OK", len(lines), "Zeilen")
