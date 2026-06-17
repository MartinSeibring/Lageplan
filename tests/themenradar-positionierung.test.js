"use strict";

// Regressionstest für die Blip-Positionierung im Themenradar.
//
// Hintergrund: Es bestand der Verdacht, dass die Kategorie "marktlich"
// (Zentrumswinkel 0°) durch den 0°/360°-Übergang ihrer ±40°-Streuung
// optisch in den falschen Quadranten rutscht. Die Analyse hat das nicht
// bestätigt — dieser Test fixiert die korrekte (symmetrische) Streuung
// für alle vier Kategorien dauerhaft, damit künftige Änderungen an
// berechnePositionen() diese Eigenschaft nicht versehentlich brechen.
//
// Die Funktion wird NICHT neu implementiert oder aus index.html kopiert,
// sondern zur Laufzeit direkt aus index.html extrahiert und ausgeführt,
// damit der Test immer die echte Produktionslogik prüft.

const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert");
const { describe, it } = require("node:test");

const INDEX_HTML_PATH = path.join(__dirname, "..", "index.html");
const SOURCE = fs.readFileSync(INDEX_HTML_PATH, "utf8");

// Extrahiert den Funktionskörper { ... } direkt nach `signature` aus `source`,
// brace-balanciert und string-aware (damit Klammern in String-Literalen
// die Zählung nicht stören). Sucht über den literalen Funktionsnamen,
// nicht über Zeilennummern — bleibt also stabil, wenn sich index.html
// an anderer Stelle ändert.
function extractFunctionBody(source, signature) {
  const sigIndex = source.indexOf(signature);
  if (sigIndex === -1) {
    throw new Error(`Signatur nicht gefunden: ${signature}`);
  }
  const braceStart = source.indexOf("{", sigIndex);
  let depth = 0;
  let inString = null;
  for (let i = braceStart; i < source.length; i++) {
    const ch = source[i];
    if (inString) {
      if (ch === inString && source[i - 1] !== "\\") inString = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") {
      inString = ch;
      continue;
    }
    if (ch === "{") {
      depth++;
    } else if (ch === "}") {
      depth--;
      if (depth === 0) {
        return source.slice(braceStart + 1, i);
      }
    }
  }
  throw new Error(`Unausgeglichene Klammern für Signatur: ${signature}`);
}

const berechnePositionenBody = extractFunctionBody(
  SOURCE,
  "function berechnePositionen()"
);

// Baut die echte Produktionsfunktion nach, mit radarData/radiusMap/farbMap
// als injizierte Parameter statt geschlossener Variablen aus index.html.
const berechnePositionen = new Function(
  "radarData",
  "radiusMap",
  "farbMap",
  berechnePositionenBody
);

const RADIUS_MAP = { kurzfristig: 100, mittelfristig: 200, langfristig: 280 };
const FARB_MAP = {
  regulatorisch: "#2d7a8e",
  marktlich: "#63a2b4",
  technologisch: "#4a8a6f",
  wettbewerblich: "#7a6ea0",
};
const ZENTRUM_GRAD = {
  regulatorisch: 270,
  marktlich: 0,
  technologisch: 90,
  wettbewerblich: 180,
};
const KATEGORIEN = Object.keys(ZENTRUM_GRAD);
const EPSILON = 1e-9;

function macheEintrag(titel, kategorie, zeithorizont, extra) {
  return Object.assign(
    {
      id: titel + "-" + kategorie + "-" + zeithorizont,
      titel,
      kategorie,
      zeithorizont,
      auswirkung: 3,
      unsicherheit: 1,
    },
    extra
  );
}

function normalizeDeg(deg) {
  return ((deg % 360) + 360) % 360;
}

function winkelVonPunkt(d) {
  const grad = (Math.atan2(d.y - 300, d.x - 300) * 180) / Math.PI;
  return normalizeDeg(grad);
}

function radiusVonPunkt(d) {
  return Math.hypot(d.x - 300, d.y - 300);
}

describe("Themenradar: berechnePositionen() Symmetrie", () => {
  it("verteilt eine 3er-Gruppe symmetrisch ±40° um den Kategorie-Zentrumswinkel (für jede Kategorie)", () => {
    for (const kategorie of KATEGORIEN) {
      const radarData = [
        macheEintrag("A", kategorie, "kurzfristig"),
        macheEintrag("B", kategorie, "kurzfristig"),
        macheEintrag("C", kategorie, "kurzfristig"),
      ];
      berechnePositionen(radarData, RADIUS_MAP, FARB_MAP);

      const zentrum = ZENTRUM_GRAD[kategorie];
      const [a, b, c] = radarData;

      // Mittlerer Punkt (alphabetisch "B") liegt exakt auf dem Zentrumswinkel.
      assert.ok(
        Math.abs(winkelVonPunkt(b) - normalizeDeg(zentrum)) < 1e-6,
        `Mittelpunkt von ${kategorie} sollte auf ${zentrum}° liegen, war ${winkelVonPunkt(b)}°`
      );

      // Äußere Punkte liegen symmetrisch bei zentrum-40° und zentrum+40°.
      assert.ok(
        Math.abs(winkelVonPunkt(a) - normalizeDeg(zentrum - 40)) < 1e-6,
        `Erster Punkt von ${kategorie} sollte auf ${normalizeDeg(zentrum - 40)}° liegen, war ${winkelVonPunkt(a)}°`
      );
      assert.ok(
        Math.abs(winkelVonPunkt(c) - normalizeDeg(zentrum + 40)) < 1e-6,
        `Letzter Punkt von ${kategorie} sollte auf ${normalizeDeg(zentrum + 40)}° liegen, war ${winkelVonPunkt(c)}°`
      );

      // Alle drei Punkte derselben Zeithorizont-Gruppe haben denselben Radius.
      assert.ok(Math.abs(radiusVonPunkt(a) - 100) < EPSILON);
      assert.ok(Math.abs(radiusVonPunkt(b) - 100) < EPSILON);
      assert.ok(Math.abs(radiusVonPunkt(c) - 100) < EPSILON);
    }
  });

  it("lässt 'marktlich'-Punkte beim 0°/360°-Übergang im rechten Quadranten (x > 300), nicht im Nachbar-Quadranten (Regressionsschutz)", () => {
    const radarData = [
      macheEintrag("A", "marktlich", "kurzfristig"),
      macheEintrag("B", "marktlich", "kurzfristig"),
      macheEintrag("C", "marktlich", "kurzfristig"),
    ];
    berechnePositionen(radarData, RADIUS_MAP, FARB_MAP);
    const [a, b, c] = radarData; // Winkel: 320°, 0°, 40°

    // Alle drei Punkte müssen rechts vom Zentrum liegen (x > 300) —
    // keiner darf in den linken Halbkreis (wettbewerblich-Bereich) rutschen.
    assert.ok(a.x > 300, `Punkt bei 320° sollte x > 300 haben, war x=${a.x}`);
    assert.ok(b.x > 300, `Punkt bei 0° sollte x > 300 haben, war x=${b.x}`);
    assert.ok(c.x > 300, `Punkt bei 40° sollte x > 300 haben, war x=${c.x}`);

    // 320° liegt oberhalb der Mittelachse (y < 300, da sin(320°) < 0),
    // 40° liegt unterhalb (y > 300, da sin(40°) > 0) — beide noch klar
    // getrennt von den oberen/unteren Quadranten (regulatorisch/technologisch).
    assert.ok(a.y < 300, `Punkt bei 320° sollte y < 300 haben, war y=${a.y}`);
    assert.ok(c.y > 300, `Punkt bei 40° sollte y > 300 haben, war y=${c.y}`);
  });

  it("platziert eine Einzelpunkt-Gruppe exakt auf dem Zentrumswinkel (keine Streuung)", () => {
    for (const kategorie of KATEGORIEN) {
      const radarData = [macheEintrag("Solo", kategorie, "mittelfristig")];
      berechnePositionen(radarData, RADIUS_MAP, FARB_MAP);
      const [d] = radarData;
      const zentrum = ZENTRUM_GRAD[kategorie];

      assert.ok(
        Math.abs(winkelVonPunkt(d) - normalizeDeg(zentrum)) < 1e-6,
        `Einzelpunkt von ${kategorie} sollte auf ${zentrum}° liegen, war ${winkelVonPunkt(d)}°`
      );
      assert.ok(Math.abs(radiusVonPunkt(d) - 200) < EPSILON);
    }
  });

  it("weist jedem Zeithorizont den korrekten Radius aus radiusMap zu", () => {
    const radarData = [
      macheEintrag("Kurz", "regulatorisch", "kurzfristig"),
      macheEintrag("Mittel", "regulatorisch", "mittelfristig"),
      macheEintrag("Lang", "regulatorisch", "langfristig"),
    ];
    berechnePositionen(radarData, RADIUS_MAP, FARB_MAP);
    const [kurz, mittel, lang] = radarData;

    assert.ok(Math.abs(radiusVonPunkt(kurz) - 100) < EPSILON);
    assert.ok(Math.abs(radiusVonPunkt(mittel) - 200) < EPSILON);
    assert.ok(Math.abs(radiusVonPunkt(lang) - 280) < EPSILON);
  });

  it("weist jeder Kategorie die korrekte Farbe aus farbMap zu", () => {
    const radarData = KATEGORIEN.map((kategorie) =>
      macheEintrag("X", kategorie, "kurzfristig")
    );
    berechnePositionen(radarData, RADIUS_MAP, FARB_MAP);

    for (const d of radarData) {
      assert.strictEqual(d.farbe, FARB_MAP[d.kategorie]);
    }
  });
});
