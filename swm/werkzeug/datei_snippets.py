BUTTONS = '''      <button class="app-datei-btn" id="btn-daten-export" onclick="DATEI.exportieren()" title="Alle Daten als JSON-Datei speichern">&#8595; Exportieren<span id="datei-dirty" title="Ungesicherte Änderungen seit dem letzten Export">&#9679;</span></button>
      <button class="app-datei-btn" id="btn-daten-import" onclick="document.getElementById('datei-import-input').click()" title="Daten aus JSON-Datei laden (ersetzt den aktuellen Stand)">&#8593; Importieren</button>
      <input type="file" id="datei-import-input" accept=".json,application/json" style="display:none" onchange="DATEI.importieren(this)">'''

CSS = '''.app-datei-btn { font-weight: 600; font-size: 12px; }
#datei-dirty { display: none; color: #f5a623; margin-left: 6px; font-size: 11px; }
#datei-dirty.sichtbar { display: inline; }
#datei-banner {
  display: none; position: fixed; top: 12px; left: 50%; transform: translateX(-50%);
  z-index: 3000; padding: 8px 16px; border-radius: 6px; color: #fff;
  font-size: 13px; font-weight: 600; box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}'''

MODUL = r'''<script>/* ===== Datei: Export / Import (Gesamt-JSON) ===== */
(function() {
  var FORMAT  = "lageplan-daten";
  var VERSION = 1;
  var HASH_KEY = lsKey("export-hash");

  function sammle() {
    return {
      themen:       (window.TR && TR.getDaten) ? TR.getDaten() : [],
      meilensteine: (window.MS && MS.getDaten) ? MS.getDaten() : [],
      ziele:        (window.MS && MS.getZiele) ? MS.getZiele() : [],
      risiken:      (window.RM && RM.getDaten) ? RM.getDaten() : []
    };
  }

  // Einfacher Fingerabdruck des Datenstands (für "ungesicherte Änderungen")
  function hash(obj) {
    var s = JSON.stringify(obj), h = 0;
    for (var i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; }
    return String(h) + ":" + s.length;
  }
  function merkeStand() {
    try { localStorage.setItem(HASH_KEY, hash(sammle())); } catch (e) {}
    pruefe();
  }
  function istGeaendert() {
    var alt = null;
    try { alt = localStorage.getItem(HASH_KEY); } catch (e) {}
    return alt !== null && alt !== hash(sammle());
  }
  function pruefe() {
    var el = document.getElementById("datei-dirty");
    if (el) el.classList.toggle("sichtbar", istGeaendert());
  }

  function banner(text, farbe) {
    var b = document.getElementById("datei-banner");
    if (!b) {
      b = document.createElement("div");
      b.id = "datei-banner";
      document.body.appendChild(b);
    }
    b.textContent = text;
    b.style.background = farbe || "#27ae60";
    b.style.display = "block";
    clearTimeout(banner._t);
    banner._t = setTimeout(function() { b.style.display = "none"; }, 4000);
  }

  // Lokaler Zeitstempel für den Dateinamen, z. B. 2026-11-17_15-24-08
  // (Ortszeit, damit mehrere Exporte am selben Tag unterscheidbar sind)
  function zeitstempel(d) {
    function z(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear() + "-" + z(d.getMonth() + 1) + "-" + z(d.getDate()) + "_" +
           z(d.getHours()) + "-" + z(d.getMinutes()) + "-" + z(d.getSeconds());
  }

  function exportieren() {
    var daten = sammle();
    var jetzt = new Date();
    var paket = {
      format: FORMAT, version: VERSION,
      exportiert: jetzt.toISOString(),
      exportiert_lokal: jetzt.toLocaleString("de-DE"),
      themen: daten.themen, meilensteine: daten.meilensteine,
      ziele: daten.ziele, risiken: daten.risiken
    };
    var blob = new Blob([JSON.stringify(paket, null, 2)], { type: "application/json" });
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement("a");
    a.href = url;
    a.download = "lageplan-daten-" + zeitstempel(jetzt) + ".json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
    merkeStand();
    banner("✓ Daten exportiert (" + daten.themen.length + " Themen, " +
           daten.meilensteine.length + " Meilensteine, " + daten.ziele.length + " Ziele, " +
           daten.risiken.length + " Risiken)");
  }

  // Erkennt Gesamt-Export sowie ältere Einzel-Exporte (reine Arrays)
  function erkenne(json) {
    if (json && !Array.isArray(json) && typeof json === "object") {
      if (json.format && json.format !== FORMAT) throw new Error("Unbekanntes Dateiformat: " + json.format);
      var teile = {};
      ["themen", "meilensteine", "ziele", "risiken"].forEach(function(k) {
        if (json[k] !== undefined) {
          if (!Array.isArray(json[k])) throw new Error("Feld '" + k + "' ist keine Liste");
          teile[k] = json[k];
        }
      });
      if (!Object.keys(teile).length) throw new Error("Keine Lageplan-Daten in der Datei gefunden");
      return teile;
    }
    if (Array.isArray(json)) {
      if (!json.length) throw new Error("Die Datei enthält eine leere Liste");
      var e = json[0] || {};
      if (e.zeithorizont !== undefined || e.radar_score !== undefined) return { themen: json };
      if (e.deadline !== undefined || /^M\d+/.test(String(e.id || ""))) return { meilensteine: json };
      if (e.eintrittswahrscheinlichkeit !== undefined || e.risikotyp !== undefined) return { risiken: json };
      throw new Error("Inhalt der Liste nicht erkannt (weder Themen noch Meilensteine noch Risiken)");
    }
    throw new Error("Unbekanntes Dateiformat");
  }

  var NAMEN = { themen: "Themen", meilensteine: "Meilensteine", ziele: "Jahresziele", risiken: "Risiken" };

  function importieren(input) {
    var file = input && input.files && input.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(ev) {
      input.value = "";
      var teile;
      try { teile = erkenne(JSON.parse(ev.target.result)); }
      catch (e) { banner("⚠ Import fehlgeschlagen: " + e.message, "#c0392b"); return; }
      var liste = Object.keys(teile).map(function(k) { return teile[k].length + " " + NAMEN[k]; }).join(", ");
      var warnung = istGeaendert() ? "\n\nACHTUNG: Es gibt Änderungen, die noch nicht exportiert wurden." : "";
      if (!confirm("Datei „" + file.name + "“ importieren?\n\nEnthält: " + liste +
                   "\n\nDer aktuelle Stand dieser Bereiche wird ersetzt." + warnung)) return;
      if (teile.themen       && window.TR) TR.ladeDaten(teile.themen);
      if (teile.meilensteine && window.MS) MS.ladeDaten(teile.meilensteine);
      if (teile.ziele        && window.MS) MS.ladeZiele(teile.ziele);
      if (teile.risiken      && window.RM) RM.ladeDaten(teile.risiken);
      try { localStorage.setItem(lsKey("last_update"), new Date().toLocaleString("de-DE")); } catch (e) {}
      try { if (window.LP && LP.aktualisiereStatusleiste) LP.aktualisiereStatusleiste(); } catch (e) {}
      try { if (window.LP && LP.zeichneLpRadar) LP.zeichneLpRadar(false); } catch (e) {}
      try { if (window.MS && MS.refresh) MS.refresh(); } catch (e) {}
      try { if (window.RM && RM.renderTab) RM.renderTab(); } catch (e) {}
      merkeStand();
      banner("✓ Importiert: " + liste);
    };
    reader.onerror = function() { banner("⚠ Datei konnte nicht gelesen werden", "#c0392b"); };
    reader.readAsText(file, "utf-8");
  }

  // Erststart: aktuellen Stand als Referenz merken
  try { if (localStorage.getItem(HASH_KEY) === null) merkeStand(); } catch (e) {}
  pruefe();
  setInterval(pruefe, 1500);
  document.addEventListener("click", function() { setTimeout(pruefe, 200); }, true);

  window.addEventListener("beforeunload", function(e) {
    if (istGeaendert()) { e.preventDefault(); e.returnValue = ""; return ""; }
  });

  window.DATEI = { exportieren: exportieren, importieren: importieren, istGeaendert: istGeaendert };
})();
</script>'''
