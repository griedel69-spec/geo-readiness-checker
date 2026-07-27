# GEO-Optimierungspaket — Word-Report-Vorlage (GEO-Radar-Design)

Verbindliche Vorlage für **jedes** ausgelieferte GEO-Optimierungspaket-Dokument
(das bezahlte € 149-Produkt, 7–8 Bausteine). Erzeugt ein gebrandetes `.docx`
im selben Design wie die Live-App (`geo_checker_app.py`) und das kostenlose
Kurz-Befund-PDF (`befund_pdf.py`) — dieselbe GEO-Radar-Sub-Marke (dunkles
Navy + Gold), nicht das allgemeine grün/orange Beratungs-CI.

## Warum eine eigene Sub-Marke?

Der GEO-Radar hat bewusst eine eigene Optik, seit dem Aufbau der Live-App
konsistent verwendet — vergleichbar mit ReviewRadar, das ebenfalls eine
eigene Bildsprache hat. Alle GEO-Radar-Deliverables (App, Kurz-Befund-PDF,
Optimierungspaket-Word-Dokument) ziehen aus derselben Palette.

## Farben (verbindlich, nicht verändern)

| Zweck | Hex |
|---|---|
| Navy (Header/Footer-Flächen, Fließtext) | `#1A2332` |
| Gold (Akzent, Überschriften auf Navy) | `#C9A84C` |
| Grün (Ampel GRÜN) | `#27AE60` |
| Orange (Ampel GELB) | `#E67E22` |
| Rot (Ampel ROT) | `#C0392B` |
| Grau (Ampel UNBEKANNT) | `#7F8C8D` |
| Cream (Hervorhebungs-Flächen) | `#F8F6F0` |
| Rahmen (neutral) | `#E8E4DC` |
| Fließtext grau | `#555555` |

Schrift: **Archivo** (Überschriften, bold) + **Open Sans** (Fließtext) —
dieselbe Paarung wie im übrigen Wort-Dokument-Kanon von Gernot Riedel
Tourism Consulting (siehe Design-Skill `gernot-riedel-tourism-consulting-design`).

## Nutzung

```bash
cd templates/geo_optimierungspaket
npm install docx   # einmalig, falls nicht global verfügbar
node generate_report.js <input.report.json> <output.docx>
```

`example.report.json` ist ein vollständiges, echtes Beispiel (Hotel
Glocknerhof) — als Referenz zum Kopieren und Anpassen.

## Report-JSON-Format

```jsonc
{
  "cover": { "title": "GEO-OPTIMIERUNGSPAKET", "subtitle": "<Hausname> — <Ort>" },
  "infoTable": [["GESAMT-AMPEL", "..."], ["Website", "..."], ["Geprüft am", "..."], ["Leistung", "..."]],
  "blocks": [ /* siehe Block-Typen unten, in Ausgabe-Reihenfolge */ ],
  "footer": { "name": "Gernot Riedel Tourism Consulting e.U.", "contact": "kontakt@gernot-riedel.com · +43 676 7237811 · gernot-riedel.com" }
}
```

### Block-Typen (`blocks[]`)

| `type` | Pflichtfelder | Darstellung |
|---|---|---|
| `h1` | `text` | Abschnitts-Überschrift, Navy/Archivo, goldene Unterstreichung |
| `ampel` | `num`, `name`, `status` (`GRÜN`\|`GELB`\|`ROT`\|`UNBEKANNT`), `text` | Weiße Karte, linker Rand in Ampelfarbe — für die 3 GEO-Radar-Signale |
| `highlight` | `text` | Cream-Box mit goldenem Rahmen rundum — für die Gesamt-Ampel-Zusammenfassung |
| `p` | `text` | Normaler Fließtext-Absatz |
| `label` | `text` | Kleine fette Navy-Zwischenüberschrift (automatisch GROSSGESCHRIEBEN), z. B. „Befund zu diesem Baustein“, „Einfügen“, „Agentur-Briefing“, „Checkliste“ |
| `sublabel` | `text` | Kleinere fette Navy-Zeile ohne Versalien, z. B. „A) Startseite (132 Zeichen):“ |
| `note` | `text` | Kleine graue Kursiv-Notiz, z. B. Zeichen-/Wortzahl |
| `bullet` | `text` | Aufzählungspunkt (goldener Punkt) |
| `checkbullet` | `text` | Aufzählungspunkt mit grünem Häkchen — **nur** innerhalb einer „Checkliste“ |
| `quote` | `text` | Cream-Box mit goldenem linkem Rand, kursiv — für wörtliche Agentur-Briefings |
| `code` | `text` (mit `\n` für Zeilenumbrüche) | Grau schattierte Monospace-Box — für JSON-LD/Code zum 1:1-Einsetzen |

**Reihenfolge-Konvention** (aus dem Referenzbeispiel abgeleitet, pro Baustein):
`h1` → kurzer `p`-Intro → `label` „Befund zu diesem Baustein“ → `p`/`bullet`(s)
→ ggf. `label` „…zum Einsetzen“ + `code` → `label` „Einfügen“ → `p` →
`label` „Agentur-Briefing“ → `quote` → `label` „Checkliste“ → `checkbullet`(s).
Nicht jeder Baustein braucht jeden Schritt — nur vorhandene Blöcke ausgeben.

## Verbindlich für alle künftigen Betriebs-Reports

Jedes GEO-Optimierungspaket-Word-Dokument für einen Betrieb wird mit
diesem Generator erzeugt, nicht freihändig in Word formatiert. Der
Skill `geo-checker-tourism` verweist auf diese Vorlage.
