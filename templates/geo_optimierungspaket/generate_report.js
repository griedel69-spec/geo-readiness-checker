#!/usr/bin/env node
/**
 * GEO-Optimierungspaket — Word-Report-Generator im GEO-Radar-Design.
 *
 * Rendert ein Report-JSON (siehe README.md fuer das Format, example.report.json
 * fuer ein vollstaendiges Beispiel) zu einem gebrandeten .docx. Farben/Fonts
 * sind identisch zur Live-App (geo_checker_app.py) und dem kostenlosen
 * Kurz-Befund-PDF (befund_pdf.py) — dieselbe Sub-Marke, nur als Word-Dokument
 * fuer das bezahlte 8-Bausteine-Paket.
 *
 * Usage:
 *   node generate_report.js <input.report.json> <output.docx>
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow,
  TableCell, WidthType, ShadingType, BorderStyle, AlignmentType,
  LevelFormat, convertInchesToTwip,
} = require("docx");

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error("Usage: node generate_report.js <input.report.json> <output.docx>");
  process.exit(1);
}
const dsl = JSON.parse(fs.readFileSync(path.resolve(inputPath), "utf-8"));

// ---- GEO-Radar Markenfarben (identisch zu geo_checker_app.py / befund_pdf.py) ----
const NAVY = "1A2332";
const GOLD = "C9A84C";
const GREEN = "27AE60";
const ORANGE = "E67E22";
const RED = "C0392B";
const CREAM = "F8F6F0";
const BORDER = "E8E4DC";
const TEXT_DARK = "1A2332";
const TEXT_GRAY = "555555";
const WHITE = "FFFFFF";

const AMPEL = { "GRÜN": GREEN, "GELB": ORANGE, "ROT": RED, "UNBEKANNT": "7F8C8D" };

const FONT_HEAD = "Archivo";
const FONT_BODY = "Open Sans";

const CONTENT_W = 9639; // A4 minus ~0.8in Raender, in DXA

function noBorder() {
  return { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
}
function fullTableBorders() {
  return { top: noBorder(), bottom: noBorder(), left: noBorder(), right: noBorder(), insideHorizontal: noBorder(), insideVertical: noBorder() };
}
function singleCellTable(cellChildren, { fill = WHITE, borders = {} } = {}) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [CONTENT_W],
    borders: fullTableBorders(),
    rows: [new TableRow({ children: [
      new TableCell({
        width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill, color: "auto" },
        margins: { top: 200, bottom: 200, left: 260, right: 260 },
        borders: {
          top: noBorder(), bottom: noBorder(), left: noBorder(), right: noBorder(),
          ...borders,
        },
        children: cellChildren,
      }),
    ] }),
  ] });
}

// ---------- Cover band (navy, gold title) ----------
function coverBand(title, subtitle) {
  return singleCellTable([
    new Paragraph({ spacing: { after: 80 }, children: [
      new TextRun({ text: title, font: FONT_HEAD, bold: true, size: 52, color: GOLD }),
    ] }),
    new Paragraph({ children: [
      new TextRun({ text: subtitle, font: FONT_BODY, size: 26, color: WHITE }),
    ] }),
  ], { fill: NAVY });
}

// ---------- Info-Tabelle (Label/Wert-Paare, z.B. Website / Geprueft am / Leistung) ----------
function infoTable(rows) {
  const labelW = 2600;
  const tableRows = rows.map((pair) => new TableRow({
    children: [
      new TableCell({
        width: { size: labelW, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: CREAM, color: "auto" },
        margins: { top: 120, bottom: 120, left: 250, right: 150 },
        borders: {
          top: { style: BorderStyle.SINGLE, size: 2, color: BORDER },
          bottom: { style: BorderStyle.SINGLE, size: 2, color: BORDER },
          left: { style: BorderStyle.SINGLE, size: 2, color: BORDER },
          right: noBorder(),
        },
        children: [new Paragraph({ children: [new TextRun({ text: pair[0], font: FONT_BODY, bold: true, size: 18, color: NAVY })] })],
      }),
      new TableCell({
        width: { size: CONTENT_W - labelW, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: CREAM, color: "auto" },
        margins: { top: 120, bottom: 120, left: 150, right: 250 },
        borders: {
          top: { style: BorderStyle.SINGLE, size: 2, color: BORDER },
          bottom: { style: BorderStyle.SINGLE, size: 2, color: BORDER },
          left: noBorder(),
          right: { style: BorderStyle.SINGLE, size: 2, color: BORDER },
        },
        children: [new Paragraph({ children: [new TextRun({ text: pair[1], font: FONT_BODY, size: 18, color: TEXT_DARK })] })],
      }),
    ],
  }));
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [labelW, CONTENT_W - labelW],
    rows: tableRows,
    borders: fullTableBorders(),
  });
}

// ---------- Signal-Ampel-Box (weiss, dicker linker Rand in Ampelfarbe) ----------
function ampelBox(b) {
  const color = AMPEL[b.status] || "7F8C8D";
  return singleCellTable([
    new Paragraph({ spacing: { after: 40 }, children: [
      new TextRun({ text: `Signal ${b.num} (${b.name}): `, font: FONT_BODY, bold: true, size: 21, color: NAVY }),
      new TextRun({ text: b.status, font: FONT_BODY, bold: true, size: 21, color: color }),
    ] }),
    new Paragraph({ children: [new TextRun({ text: b.text, font: FONT_BODY, size: 19, color: TEXT_GRAY })] }),
  ], {
    fill: WHITE,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
      right: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
      left: { style: BorderStyle.SINGLE, size: 36, color: color },
    },
  });
}

// ---------- Gesamt-Ampel-Hervorhebung (Cream, goldener Rahmen rundum) ----------
function highlightBox(text) {
  return singleCellTable([
    new Paragraph({ children: [new TextRun({ text, font: FONT_BODY, size: 20, color: NAVY })] }),
  ], {
    fill: CREAM,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 6, color: GOLD },
      bottom: { style: BorderStyle.SINGLE, size: 6, color: GOLD },
      right: { style: BorderStyle.SINGLE, size: 6, color: GOLD },
      left: { style: BorderStyle.SINGLE, size: 6, color: GOLD },
    },
  });
}

// ---------- Agentur-Briefing / woertliches Zitat (Cream, goldener linker Rand) ----------
function quoteBox(text) {
  return singleCellTable([
    new Paragraph({ children: [new TextRun({ text, font: FONT_BODY, italics: true, size: 19, color: TEXT_DARK })] }),
  ], {
    fill: CREAM,
    borders: { left: { style: BorderStyle.SINGLE, size: 24, color: GOLD } },
  });
}

// ---------- Code-Box (z.B. JSON-LD, 1:1 zum Einsetzen) ----------
function codeBox(text) {
  const lines = text.split("\n");
  return singleCellTable(
    lines.map((line) => new Paragraph({
      spacing: { after: 0, line: 260 },
      children: [new TextRun({ text: line.length ? line : " ", font: "Consolas", size: 17, color: NAVY })],
    })),
    { fill: "F4F4F1", borders: { top: { style: BorderStyle.SINGLE, size: 2, color: BORDER }, bottom: { style: BorderStyle.SINGLE, size: 2, color: BORDER }, left: { style: BorderStyle.SINGLE, size: 2, color: BORDER }, right: { style: BorderStyle.SINGLE, size: 2, color: BORDER } } },
  );
}

// ---------- Footer-Band ----------
function footerBand(name, contact) {
  return singleCellTable([
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [new TextRun({ text: name, font: FONT_BODY, bold: true, size: 20, color: GOLD })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: contact, font: FONT_BODY, size: 17, color: "C7CBD1" })] }),
  ], { fill: NAVY });
}

// ---------- Fliesstext-Bausteine ----------
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 420, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: GOLD, space: 6 } },
    children: [new TextRun({ text, font: FONT_HEAD, bold: true, size: 27, color: NAVY })],
  });
}
function p(text) {
  return new Paragraph({ spacing: { after: 160, line: 300 }, children: [new TextRun({ text, font: FONT_BODY, size: 21, color: TEXT_DARK })] });
}
function label(text) {
  return new Paragraph({
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text: text.toUpperCase(), font: FONT_BODY, bold: true, size: 17, color: NAVY, characterSpacing: 12 })],
  });
}
function sublabel(text) {
  return new Paragraph({ spacing: { before: 120, after: 40 }, children: [new TextRun({ text, font: FONT_BODY, bold: true, size: 19, color: NAVY })] });
}
function note(text) {
  return new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text, font: FONT_BODY, italics: true, size: 17, color: TEXT_GRAY })] });
}
function bullet(text, ref) {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 100, line: 290 },
    children: [new TextRun({ text, font: FONT_BODY, size: 20, color: TEXT_DARK })],
  });
}

// ---------- Dokument zusammensetzen ----------
const body = [];
body.push(coverBand(dsl.cover.title, dsl.cover.subtitle));
body.push(new Paragraph({ spacing: { after: 200 }, children: [] }));
if (dsl.infoTable && dsl.infoTable.length) {
  body.push(infoTable(dsl.infoTable));
  body.push(new Paragraph({ spacing: { after: 100 }, children: [] }));
}

for (const b of dsl.blocks) {
  switch (b.type) {
    case "h1": body.push(h1(b.text)); break;
    case "ampel": body.push(ampelBox(b)); body.push(new Paragraph({ spacing: { after: 100 }, children: [] })); break;
    case "highlight": body.push(highlightBox(b.text)); body.push(new Paragraph({ spacing: { after: 160 }, children: [] })); break;
    case "p": body.push(p(b.text)); break;
    case "label": body.push(label(b.text)); break;
    case "sublabel": body.push(sublabel(b.text)); break;
    case "note": body.push(note(b.text)); break;
    case "bullet": body.push(bullet(b.text, "geoBullets")); break;
    case "checkbullet": body.push(bullet(b.text, "geoCheckBullets")); break;
    case "quote": body.push(quoteBox(b.text)); body.push(new Paragraph({ spacing: { after: 160 }, children: [] })); break;
    case "code": body.push(codeBox(b.text)); body.push(new Paragraph({ spacing: { after: 160 }, children: [] })); break;
    default:
      console.warn(`Unbekannter Block-Typ uebersprungen: ${b.type}`);
  }
}

body.push(new Paragraph({ spacing: { after: 200 }, children: [] }));
body.push(footerBand(dsl.footer.name, dsl.footer.contact));

const doc = new Document({
  title: `${dsl.cover.title} – ${dsl.cover.subtitle}`,
  creator: "Gernot Riedel Tourism Consulting e.U.",
  numbering: {
    config: [
      {
        reference: "geoBullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 420, hanging: 260 } }, run: { color: GOLD, font: FONT_BODY } } }],
      },
      {
        reference: "geoCheckBullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "✓", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 420, hanging: 260 } }, run: { color: GREEN, font: FONT_BODY, bold: true } } }],
      },
    ],
  },
  styles: { default: { document: { run: { font: FONT_BODY, size: 21, color: TEXT_DARK } } } },
  sections: [{
    properties: { page: { margin: {
      top: convertInchesToTwip(0.7), bottom: convertInchesToTwip(0.7),
      left: convertInchesToTwip(0.8), right: convertInchesToTwip(0.8),
    } } },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.resolve(outputPath), buf);
  console.log(`geschrieben: ${outputPath} (${buf.length} bytes)`);
});
