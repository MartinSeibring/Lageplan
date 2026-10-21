"use strict";

// Tests für die Sortierung der Themenradar-Listenansicht (sortiereThemen).
//
// Wie im Positionierungstest wird die Funktion nicht nachgebaut, sondern
// zur Laufzeit aus index.html extrahiert, damit immer die echte
// Produktionslogik geprüft wird.

const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert");
const { describe, it } = require("node:test");

const SOURCE = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

// Brace-balancierte, string-aware Extraktion des Funktionskörpers
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

const sortiereThemen = new Function(
  "daten",
  "modus",
  extractFunctionBody(SOURCE, "function sortiereThemen(daten, modus)")
);

function thema(titel, zeithorizont, score, cluster) {
  return { id: titel, titel, zeithorizont, radar_score: score, strategische_cluster: cluster };
}

const DATEN = [
  thema("A", "langfristig",   0.42, ["Technologie"]),
  thema("B", "kurzfristig",   0.92, ["Messstellenbetrieb", "Netzwirtschaft"]),
  thema("C", "mittelfristig", 0.68, ["Netzanschluss"]),
  thema("D", "kurzfristig",   0.84, []),
  thema("E", "mittelfristig", 0.68, ["Netzwirtschaft"]),
];

const titel = gruppe => gruppe.themen.map(t => t.titel);

describe("sortiereThemen", () => {
  it("score: eine Gruppe, Score absteigend, Gleichstand nach Titel", () => {
    const gruppen = sortiereThemen(DATEN, "score");
    assert.strictEqual(gruppen.length, 1);
    assert.strictEqual(gruppen[0].titel, null);
    assert.deepStrictEqual(titel(gruppen[0]), ["B", "D", "C", "E", "A"]);
  });

  it("unbekannter Modus fällt auf score zurück", () => {
    assert.deepStrictEqual(titel(sortiereThemen(DATEN, "xyz")[0]), ["B", "D", "C", "E", "A"]);
  });

  it("zeit: Gruppen kurz → mittel → lang, darin Score absteigend", () => {
    const gruppen = sortiereThemen(DATEN, "zeit");
    assert.deepStrictEqual(gruppen.map(g => g.titel), [
      "Kurzfristig (0–1 Jahr)", "Mittelfristig (1–3 Jahre)", "Langfristig (> 3 Jahre)",
    ]);
    assert.deepStrictEqual(gruppen.map(titel), [["B", "D"], ["C", "E"], ["A"]]);
  });

  it("cluster: feste Reihenfolge, leere Gruppen entfallen, 'Ohne Cluster' am Ende", () => {
    const gruppen = sortiereThemen(DATEN, "cluster");
    assert.deepStrictEqual(gruppen.map(g => g.titel), [
      "Netzanschluss", "Messstellenbetrieb", "Netzwirtschaft", "Technologie", "Ohne Cluster",
    ]);
    assert.deepStrictEqual(titel(gruppen[4]), ["D"]);
  });

  it("cluster: Thema mit zwei Clustern steht in beiden Gruppen", () => {
    const gruppen = sortiereThemen(DATEN, "cluster");
    const mitB = gruppen.filter(g => titel(g).includes("B")).map(g => g.titel);
    assert.deepStrictEqual(mitB, ["Messstellenbetrieb", "Netzwirtschaft"]);
    assert.deepStrictEqual(titel(gruppen.find(g => g.titel === "Netzwirtschaft")), ["B", "E"]);
  });

  it("cluster: unbekannte Cluster bekommen eine eigene Gruppe nach den Standard-Clustern", () => {
    const gruppen = sortiereThemen([thema("X", "kurzfristig", 0.5, ["Zukunft"])], "cluster");
    assert.deepStrictEqual(gruppen.map(g => g.titel), ["Zukunft"]);
  });

  it("verändert die Eingabe nicht", () => {
    const kopie = DATEN.map(d => d.titel);
    sortiereThemen(DATEN, "score");
    assert.deepStrictEqual(DATEN.map(d => d.titel), kopie);
  });
});
