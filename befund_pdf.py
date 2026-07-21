"""
Kurz-Befund-PDF (eine A4-Seite) für den GEO-Readiness-Checker.

Erzeugt aus dem Befund-Dict (befund.baue_befund) ein gebrandetes PDF
als Bytes — kein Netz, keine API, reine reportlab-Erzeugung.
"""
from __future__ import annotations

import datetime
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# Markenfarben (identisch zur App)
DUNKEL = colors.HexColor("#1a2332")
GOLD = colors.HexColor("#c9a84c")
GRAU = colors.HexColor("#555555")
AMPEL = {
    "GRÜN": colors.HexColor("#27ae60"),
    "GELB": colors.HexColor("#e67e22"),
    "ROT": colors.HexColor("#c0392b"),
    "UNBEKANNT": colors.HexColor("#7f8c8d"),
}

_BASIS = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=DUNKEL)
STYLES = {
    "titel": ParagraphStyle("titel", fontName="Helvetica-Bold", fontSize=20,
                            leading=24, textColor=colors.white),
    "untertitel": ParagraphStyle("untertitel", fontName="Helvetica", fontSize=10,
                                 leading=13, textColor=colors.HexColor("#e8c97a")),
    "normal": ParagraphStyle("normal", **_BASIS),
    "klein": ParagraphStyle("klein", fontName="Helvetica", fontSize=8,
                            leading=11, textColor=GRAU),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12,
                         leading=16, textColor=DUNKEL, spaceBefore=6),
    "ampel_gross": ParagraphStyle("ampel_gross", fontName="Helvetica-Bold",
                                  fontSize=22, leading=26, textColor=colors.white,
                                  alignment=1),
    "ampel_text": ParagraphStyle("ampel_text", fontName="Helvetica", fontSize=10,
                                 leading=14, textColor=colors.white, alignment=1),
}


def _kopf(betrieb: str, ort: str, website: str) -> list:
    kopf_tab = Table(
        [[Paragraph("GEO-Kurz-Befund", STYLES["titel"])],
         [Paragraph("Wie sichtbar ist Ihr Betrieb in ChatGPT, Perplexity &amp; Google AI?",
                    STYLES["untertitel"])]],
        colWidths=[170 * mm],
    )
    kopf_tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DUNKEL),
        ("LEFTPADDING", (0, 0), (-1, -1), 10 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10 * mm),
        ("TOPPADDING", (0, 0), (0, 0), 8 * mm),
        ("BOTTOMPADDING", (0, 1), (0, 1), 8 * mm),
    ]))
    datum = datetime.date.today().strftime("%d.%m.%Y")
    info = Paragraph(
        f"<b>{betrieb}</b> · {ort}<br/>{website} · geprüft am {datum}",
        STYLES["normal"],
    )
    return [kopf_tab, Spacer(1, 5 * mm), info, Spacer(1, 4 * mm)]


def _ampelbox(befund: dict) -> Table:
    box = Table(
        [[Paragraph(f"Gesamt-Ampel: {befund['overall']}", STYLES["ampel_gross"])],
         [Paragraph(befund["klartext"], STYLES["ampel_text"])]],
        colWidths=[170 * mm],
    )
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMPEL[befund["overall"]]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("TOPPADDING", (0, 0), (0, 0), 5 * mm),
        ("BOTTOMPADDING", (0, 1), (0, 1), 5 * mm),
    ]))
    return box


def _signaltabelle(befund: dict) -> Table:
    zeilen = [[Paragraph("<b>Prüfbereich</b>", STYLES["normal"]),
               Paragraph("<b>Ampel</b>", STYLES["normal"]),
               Paragraph("<b>Befund</b>", STYLES["normal"])]]
    for s in befund["signale"]:
        zeilen.append([
            Paragraph(s["name"], STYLES["normal"]),
            Paragraph(f'<font color="white"><b>{s["status"]}</b></font>',
                      STYLES["normal"]),
            Paragraph(s["grund"] or "—", STYLES["klein"]),
        ])
    tab = Table(zeilen, colWidths=[55 * mm, 25 * mm, 90 * mm])
    stil = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e4dc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f6f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
    ]
    for i, s in enumerate(befund["signale"], start=1):
        stil.append(("BACKGROUND", (1, i), (1, i), AMPEL[s["status"]]))
    tab.setStyle(TableStyle(stil))
    return tab


def erzeuge_kurzbefund_pdf(lead: dict, befund: dict) -> bytes:
    """Baut das einseitige Kurz-Befund-PDF und liefert es als Bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"GEO-Kurz-Befund {lead.get('betrieb', '')}",
        author="Gernot Riedel Tourism Consulting",
    )

    teile = _kopf(lead.get("betrieb", ""), lead.get("ort", ""), lead.get("website", ""))
    teile += [_ampelbox(befund), Spacer(1, 5 * mm)]
    teile += [Paragraph("Die drei Prüfbereiche im Detail", STYLES["h2"]),
              Spacer(1, 2 * mm), _signaltabelle(befund), Spacer(1, 5 * mm)]

    if befund["empfehlungen"]:
        teile.append(Paragraph("Was jetzt zu tun ist", STYLES["h2"]))
        teile.append(Spacer(1, 2 * mm))
        for i, e in enumerate(befund["empfehlungen"], 1):
            teile.append(Paragraph(f"<b>{i}.</b> {e}", STYLES["normal"]))
            teile.append(Spacer(1, 1.5 * mm))
        teile.append(Spacer(1, 3 * mm))

    if befund["verkaufsbruecke"]:
        vb = Table([[Paragraph(
            '<font color="#c9a84c"><b>Unser Angebot: GEO-Optimierungspaket Professional — € 149</b></font><br/>'
            '<font color="white">Wir setzen die oben genannten Punkte in fertige, KI-lesbare Texte um: '
            'FAQ, Startseiten-Überschrift, USP-Box, lokale Keywords, Google-Business-Text, '
            'Meta-Descriptions und ein neuer "Über uns"-Text — geliefert innerhalb von 24 Stunden. '
            'Antworten Sie einfach auf diese E-Mail.</font>',
            STYLES["normal"])]], colWidths=[170 * mm])
        vb.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DUNKEL),
            ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ]))
        teile += [vb, Spacer(1, 4 * mm)]

    teile.append(Paragraph(
        "Hinweis: Automatische Kurz-Prüfung der Startseite (Signale 1–3 des GEO-Radar). "
        "Nicht erreichbare Punkte werden ehrlich als UNBEKANNT ausgewiesen — nie geraten.",
        STYLES["klein"],
    ))
    teile.append(Spacer(1, 3 * mm))
    teile.append(Paragraph(
        "<b>Gernot Riedel Tourism Consulting</b> · TÜV-zertifizierter KI-Trainer · "
        "kontakt@gernot-riedel.com · +43 676 7237811 · gernot-riedel.com",
        STYLES["klein"],
    ))

    doc.build(teile)
    return buf.getvalue()
