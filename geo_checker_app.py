import streamlit as st
import csv
import io
import datetime
import re
import time
import urllib.request
from urllib.parse import urlparse

# Google-Sheets-Lead-Register (eigenes Modul, testbar ohne Streamlit)
from sheets import SHEET_ID, get_sheet, schreibe_lead

# Gemeinsame Prüf-Logik (Signale 1-3, übernommen aus geo-radar — siehe signals/__init__.py)
from signals import check_robots, check_schema, check_rendering
from befund import baue_befund, signal_kurzzeile, AMPEL_FARBEN, AMPEL_SYMBOL
from befund_pdf import erzeuge_kurzbefund_pdf
from mailer import sende_kurzbefund

# ─── PAGE CONFIG ───
st.set_page_config(
    page_title="GEO-Readiness Checker | Gernot Riedel Tourism Consulting",
    page_icon="🏔",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── CUSTOM CSS ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1a2332 0%, #2d4a3e 100%);
    padding: 36px 32px 28px; border-radius: 8px; margin-bottom: 28px;
}
.main-header h1 { color:#fff; font-size:30px; font-weight:700; margin:0 0 8px; line-height:1.2; }
.main-header h1 span { color:#c9a84c; }
.main-header p { color:rgba(255,255,255,0.72); font-size:15px; margin:0; line-height:1.6; }
.brand-tag {
    display:inline-block; background:rgba(201,168,76,0.2);
    border:1px solid rgba(201,168,76,0.4); color:#e8c97a;
    padding:4px 12px; border-radius:2px; font-size:11px;
    font-weight:600; letter-spacing:2px; text-transform:uppercase; margin-bottom:16px;
}

.ampel-card {
    border-radius:8px; padding:28px 32px; text-align:center; margin:20px 0; color:white;
}
.ampel-status { font-size:44px; font-weight:700; line-height:1.1; }
.ampel-label { font-size:14px; opacity:0.85; margin-top:4px; letter-spacing:1px; text-transform:uppercase; }
.ampel-klartext { font-size:16px; font-weight:500; margin-top:12px; }

.signal-card {
    background:white; border:1px solid #e8e4dc; border-radius:6px;
    padding:14px 18px; margin:8px 0;
}
.signal-status {
    display:inline-block; color:white; font-weight:700; font-size:12px;
    padding:3px 10px; border-radius:3px; margin-right:8px;
}
.signal-name { font-weight:600; font-size:15px; color:#1a2332; }
.signal-grund { color:#555; font-size:13px; margin-top:5px; }

.check-ok {
    background:#f0fff4; border-left:4px solid #27ae60;
    border-radius:4px; padding:12px 16px; margin:6px 0; font-size:14px;
}
.check-fail {
    background:#fff3f3; border-left:4px solid #c0392b;
    border-radius:4px; padding:12px 16px; margin:6px 0; font-size:14px;
}
.check-name { font-weight:600; color:#1a2332; }
.check-detail { color:#555; font-size:13px; margin-top:3px; }

.quickwin-card {
    background:white; border:1px solid #e8e4dc;
    border-radius:6px; padding:14px 18px; margin:8px 0;
}
.qw-hoch   { border-left:4px solid #c0392b; }
.qw-mittel { border-left:4px solid #e67e22; }
.qw-niedrig { border-left:4px solid #27ae60; }
.qw-titel { font-weight:600; font-size:14px; color:#1a2332; }
.qw-impact { font-size:13px; color:#666; margin-top:3px; }

.robots-blocked {
    background:#fff3f3; border-left:4px solid #c0392b;
    padding:10px 14px; border-radius:4px; margin:4px 0; font-size:13px;
}
.robots-allowed {
    background:#f0fff4; border-left:4px solid #27ae60;
    padding:10px 14px; border-radius:4px; margin:4px 0; font-size:13px;
}

.cta-box {
    background:linear-gradient(135deg,#1a2332 0%,#2d4a3e 100%);
    border-radius:8px; padding:28px 32px; text-align:center; margin:24px 0; color:white;
}
.cta-box h3 { color:#c9a84c; font-size:22px; margin:0 0 10px; }
.cta-box p  { opacity:0.85; font-size:15px; margin:0 0 18px; }

.category-header {
    background:#f8f6f0; border-left:4px solid #c9a84c;
    padding:8px 14px; margin:18px 0 8px; border-radius:4px;
    font-weight:600; font-size:15px; color:#1a2332;
}

.footer-bar {
    background:#1a2332; color:rgba(255,255,255,0.6);
    text-align:center; padding:16px; border-radius:6px;
    font-size:12px; margin-top:40px;
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ───
for key, default in [
    ("analyse_done", False), ("result", None), ("lead_data", None),
    ("admin_logged_in", False), ("leads", [])
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════
# GOOGLE SHEETS
# ══════════════════════════════════════════════════════

def write_lead_to_sheet(data: dict) -> bool:
    try:
        sheet = get_sheet(dict(st.secrets["gcp_service_account"]))
        schreibe_lead(sheet, data)
        return True
    except Exception as e:
        st.warning(f"Google Sheets: {e}")
        return False


# ══════════════════════════════════════════════════════
# TECHNISCHE MESSUNG
# ══════════════════════════════════════════════════════

def check_website(url: str) -> dict:
    """
    Misst die ergänzenden technischen Faktoren direkt und verifizierbar.
    robots.txt/KI-Bots, Schema.org/JSON-LD und Textsubstanz werden NICHT mehr
    hier geprüft — das übernehmen die Signal-Module 1-3 (Ordner signals/).
    """
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    facts  = {"https": parsed.scheme == "https"}

    # sitemap.xml
    try:
        req = urllib.request.Request(
            f"{base}/sitemap.xml", headers={"User-Agent": "GEO-Checker/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            facts["sitemap_exists"] = resp.status == 200
    except Exception:
        facts["sitemap_exists"] = False

    # Ladezeit + HTML
    raw_html = ""
    try:
        t0 = time.time()
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 GEO-Checker/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_html = resp.read().decode("utf-8", errors="ignore")
        facts["load_time"] = round(time.time() - t0, 2)
        facts["load_ok"]   = facts["load_time"] < 3.0
    except Exception:
        facts["load_time"] = None
        facts["load_ok"]   = False

    # Meta-Description
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', raw_html, re.I) or \
        re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', raw_html, re.I)
    facts["meta_desc"] = m.group(1).strip() if m else ""
    facts["meta_desc_ok"] = bool(facts["meta_desc"])

    # Viewport
    facts["viewport"] = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', raw_html, re.I))

    # lang=
    lm = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', raw_html, re.I)
    facts["lang"]    = lm.group(1) if lm else ""
    facts["lang_ok"] = bool(facts["lang"])

    # Page Title
    tm = re.search(r'<title[^>]*>(.*?)</title>', raw_html, re.I | re.DOTALL)
    facts["page_title"] = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""
    facts["title_ok"]   = bool(facts["page_title"])

    # Canonical
    cm = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', raw_html, re.I)
    facts["canonical"]    = cm.group(1) if cm else ""
    facts["canonical_ok"] = bool(facts["canonical"])

    # Schema.org
    facts["schema_org"] = "schema.org" in raw_html.lower()

    # ─── NEW GEO & KI CHECKS ───

    # Open Graph Tags (og:title, og:description, og:image)
    og_title = re.search(r'<meta\s+(?:property|name)=["\']og:title["\']\s+content=["\'](.*?)["\']', raw_html, re.I) or \
               re.search(r'<meta\s+content=["\'](.*?)["\']\s+(?:property|name)=["\']og:title["\']', raw_html, re.I)
    og_desc = re.search(r'<meta\s+(?:property|name)=["\']og:description["\']\s+content=["\'](.*?)["\']', raw_html, re.I) or \
              re.search(r'<meta\s+content=["\'](.*?)["\']\s+(?:property|name)=["\']og:description["\']', raw_html, re.I)
    og_image = re.search(r'<meta\s+(?:property|name)=["\']og:image["\']\s+content=["\'](.*?)["\']', raw_html, re.I) or \
               re.search(r'<meta\s+content=["\'](.*?)["\']\s+(?:property|name)=["\']og:image["\']', raw_html, re.I)
    og_parts = []
    if og_title:  og_parts.append("og:title")
    if og_desc:   og_parts.append("og:description")
    if og_image:  og_parts.append("og:image")
    facts["og_tags_found"] = og_parts
    facts["og_ok"] = len(og_parts) >= 2  # At least title + description

    # H1 Heading
    h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', raw_html, re.I | re.DOTALL)
    facts["h1_count"] = len(h1_matches)
    facts["h1_text"] = re.sub(r'<[^>]+>', '', h1_matches[0]).strip() if h1_matches else ""
    facts["h1_ok"] = len(h1_matches) == 1 and bool(facts["h1_text"])

    # Image Alt Texts
    all_images = re.findall(r'<img\b[^>]*>', raw_html, re.I)
    images_with_alt = [img for img in all_images if re.search(r'\balt=["\'][^"\']+["\']', img, re.I)]
    facts["img_total"] = len(all_images)
    facts["img_with_alt"] = len(images_with_alt)
    facts["img_alt_pct"] = round(len(images_with_alt) / len(all_images) * 100) if all_images else 100
    facts["img_alt_ok"] = facts["img_alt_pct"] >= 80

    # JSON-LD Structured Data (preferred by AI engines over microdata/RDFa)
    jsonld_blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_html, re.I | re.DOTALL)
    facts["jsonld_count"] = len(jsonld_blocks)
    facts["jsonld_ok"] = len(jsonld_blocks) > 0
    # Detect schema types in JSON-LD
    jsonld_types = []
    for block in jsonld_blocks:
        types = re.findall(r'"@type"\s*:\s*"([^"]+)"', block)
        jsonld_types.extend(types)
    facts["jsonld_types"] = jsonld_types

    # Sufficient Text Content (word count)
    text_only = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.I | re.DOTALL)
    text_only = re.sub(r'<style[^>]*>.*?</style>', '', text_only, flags=re.I | re.DOTALL)
    text_only = re.sub(r'<[^>]+>', ' ', text_only)
    text_only = re.sub(r'\s+', ' ', text_only).strip()
    words = [w for w in text_only.split() if len(w) > 1]
    facts["word_count"] = len(words)
    facts["content_ok"] = len(words) >= 300

    # Meta Robots / Indexability
    meta_robots = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\'](.*?)["\']', raw_html, re.I) or \
                  re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']robots["\']', raw_html, re.I)
    robots_content = meta_robots.group(1).lower() if meta_robots else ""
    facts["meta_robots"] = robots_content
    facts["noindex"] = "noindex" in robots_content
    facts["nofollow"] = "nofollow" in robots_content
    facts["indexable_ok"] = not facts["noindex"]

    # Hreflang Tags (multilingual / international targeting)
    hreflang_matches = re.findall(r'<link[^>]+hreflang=["\']([^"\']+)["\']', raw_html, re.I)
    facts["hreflang_langs"] = list(set(hreflang_matches))
    facts["hreflang_ok"] = len(hreflang_matches) > 0

    # Internal Links
    all_links = re.findall(r'<a\b[^>]+href=["\']([^"\'#]+)["\']', raw_html, re.I)
    internal_links = [l for l in all_links if l.startswith("/") or parsed.netloc in l]
    facts["internal_link_count"] = len(internal_links)
    facts["internal_links_ok"] = len(internal_links) >= 3

    return facts


def build_checks(facts: dict) -> list:
    """
    Erstellt die 14 ergänzenden Checkpunkte mit Ergebnis und Quick-Win-Hinweis.

    Die Kernprüfungen (robots.txt/KI-Bots, Schema.org/JSON-LD, Textsubstanz)
    laufen NICHT mehr hier, sondern über die gemeinsamen Signal-Module 1-3
    aus dem geo-radar (Ordner signals/) — mit Ampel-Logik statt Punkten.
    """
    # Image alt text detail
    img_total = facts.get("img_total", 0)
    img_alt   = facts.get("img_with_alt", 0)
    img_pct   = facts.get("img_alt_pct", 100)

    # OG tags detail
    og_found = facts.get("og_tags_found", [])

    return [
        # ── SECTION: Technische Basis ──
        {
            "name":     "HTTPS-Verschlüsselung",
            "ok":       facts.get("https", False),
            "detail":   "Aktiv" if facts.get("https") else "Nicht aktiv",
            "quickwin": "HTTPS aktivieren — Pflicht für jede moderne Website und Vertrauenssignal für KI-Systeme.",
            "howto":    "Kontaktieren Sie Ihren Webhoster (z.B. World4You, All-Inkl, Strato) und fragen Sie nach einem kostenlosen SSL-Zertifikat (Let's Encrypt). Die meisten Hoster aktivieren das per Klick im Kundenmenü. Bei WordPress-Seiten danach unter Einstellungen → Allgemein die URL auf https:// ändern.",
            "impact":   "Sicherheit & Vertrauen",
            "category": "Technische Basis",
        },
        {
            "name":     "Ladezeit unter 3 Sekunden",
            "ok":       facts.get("load_ok", False),
            "detail":   (f"{facts['load_time']}s" if facts.get("load_time") else "Nicht messbar"),
            "quickwin": f"Ladezeit optimieren (aktuell {facts.get('load_time','?')}s) — KI-Crawler bevorzugen schnell ladende Seiten.",
            "howto":    "Die häufigsten Ursachen für langsame Seiten: (1) Bilder komprimieren — laden Sie Ihre Bilder auf tinypng.com hoch und ersetzen Sie die Originale. (2) Bei WordPress: ein Caching-Plugin installieren (z.B. WP Super Cache oder LiteSpeed Cache). (3) Prüfen Sie, ob Ihr Hosting-Paket ausreichend Leistung hat — bei sehr günstigen Paketen kann ein Upgrade auf SSD-Hosting helfen.",
            "impact":   "Crawlbarkeit & User Experience",
            "category": "Technische Basis",
        },
        {
            "name":     "Mobile Viewport-Tag",
            "ok":       facts.get("viewport", False),
            "detail":   "Vorhanden" if facts.get("viewport") else "Fehlt",
            "quickwin": "Viewport-Tag fehlt — Ihre Seite wird auf Smartphones nicht korrekt dargestellt.",
            "howto":    "Ihr Webentwickler muss eine Zeile im HTML-Kopfbereich (Head) ergänzen: <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">. Bei WordPress-Themes ist das normalerweise automatisch enthalten — prüfen Sie, ob Ihr Theme aktuell ist. Falls Sie einen Baukastensystem wie Jimdo oder Wix nutzen, ist es meist automatisch gesetzt.",
            "impact":   "Mobile Sichtbarkeit",
            "category": "Technische Basis",
        },
        {
            "name":     "Indexierbarkeit (Meta Robots)",
            "ok":       facts.get("indexable_ok", True),
            "detail":   "Indexierung erlaubt" if facts.get("indexable_ok", True) else f"BLOCKIERT — {facts.get('meta_robots', '')}",
            "quickwin": "ACHTUNG: Ihre Seite blockiert aktiv die Indexierung! Suchmaschinen UND KI-Systeme dürfen Ihre Seite nicht anzeigen.",
            "howto":    "Das passiert oft, wenn die Website nach einem Relaunch versehentlich auf 'noindex' steht. Bei WordPress: Gehen Sie zu Einstellungen → Lesen und deaktivieren Sie 'Suchmaschinen davon abhalten, diese Website zu indexieren'. Bei anderen Systemen: Bitten Sie Ihren Webentwickler, den noindex-Tag aus dem HTML-Head zu entfernen. Das ist die wichtigste Maßnahme — ohne diese Änderung sind alle anderen Optimierungen wirkungslos!",
            "impact":   "Sichtbarkeit — kritisch",
            "category": "Technische Basis",
        },
        # ── SECTION: Crawlbarkeit & Indexierung ──
        # (robots.txt/KI-Bots wird jetzt von Signal 1 geprüft — siehe Ampel oben)
        {
            "name":     "sitemap.xml vorhanden",
            "ok":       facts.get("sitemap_exists", False),
            "detail":   "Gefunden" if facts.get("sitemap_exists") else "Nicht gefunden",
            "quickwin": "sitemap.xml erstellen — das ist wie ein Inhaltsverzeichnis Ihrer Website für KI-Crawler.",
            "howto":    "Bei WordPress: Installieren Sie das Plugin 'Yoast SEO' oder 'Rank Math' — beide erstellen automatisch eine Sitemap unter IhreWebsite.at/sitemap.xml. Bei anderen Systemen: Nutzen Sie xml-sitemaps.com, um kostenlos eine Sitemap zu erzeugen, und laden Sie die Datei ins Hauptverzeichnis Ihrer Website hoch. Danach in der robots.txt ergänzen: Sitemap: https://www.ihre-website.at/sitemap.xml",
            "impact":   "Vollständige Indexierung",
            "category": "Crawlbarkeit & Indexierung",
        },
        {
            "name":     "Canonical Tag gesetzt",
            "ok":       facts.get("canonical_ok", False),
            "detail":   "Vorhanden" if facts.get("canonical_ok") else "Fehlt",
            "quickwin": "Canonical Tag ergänzen — das verhindert, dass KI-Systeme Ihre Inhalte doppelt oder falsch zuordnen.",
            "howto":    "Der Canonical Tag sagt Suchmaschinen und KI: 'Das ist die Original-Adresse dieser Seite.' Bei WordPress: Yoast SEO oder Rank Math setzen diesen Tag automatisch. Bei anderen Systemen: Ihr Webentwickler muss im HTML-Head jeder Seite ergänzen: <link rel=\"canonical\" href=\"https://www.ihre-website.at/aktuelle-seite/\">. Die URL muss jeweils die aktuelle Seitenadresse sein.",
            "impact":   "Technische SEO & KI-Indexierung",
            "category": "Crawlbarkeit & Indexierung",
        },
        {
            "name":     "Interne Verlinkung (min. 3 Links)",
            "ok":       facts.get("internal_links_ok", False),
            "detail":   f'{facts.get("internal_link_count", 0)} interne Links gefunden' if facts.get("internal_links_ok") else f'Nur {facts.get("internal_link_count", 0)} interne Links',
            "quickwin": "Mehr interne Links setzen — KI-Crawler folgen diesen Links, um Ihren Betrieb besser zu verstehen.",
            "howto":    "Verlinken Sie auf Ihrer Startseite zu den wichtigsten Unterseiten: Zimmer/Wohnungen, Preise, Lage/Anreise, Aktivitäten, Kontakt. Jeder Link hilft KI-Systemen, mehr über Ihr Angebot zu erfahren. Konkret: Schreiben Sie z.B. 'Entdecken Sie unsere Zimmer' und verlinken Sie den Text auf die Zimmer-Seite. Mindestens 3-5 interne Links auf der Startseite sind empfohlen.",
            "impact":   "Crawl-Tiefe & Kontext",
            "category": "Crawlbarkeit & Indexierung",
        },
        # ── SECTION: KI-Zitierbarkeit & Inhalte ──
        {
            "name":     "Meta-Description vorhanden",
            "ok":       facts.get("meta_desc_ok", False),
            "detail":   f'"{facts["meta_desc"][:60]}…"' if facts.get("meta_desc_ok") else "Fehlt",
            "quickwin": "Meta-Description fehlt — das ist der kurze Vorschautext, den KI-Systeme als Zusammenfassung nutzen.",
            "howto":    "Schreiben Sie eine kurze, ansprechende Beschreibung Ihres Betriebs in max. 155 Zeichen. Beispiel: '4-Sterne Wellnesshotel in Kitzbühel mit Panorama-Spa, regionaler Küche und direktem Zugang zu 170 km Skipisten.' Bei WordPress: Im Yoast SEO Plugin unter jeder Seite die 'Meta-Beschreibung' ausfüllen. Bei anderen Systemen: Ihr Webentwickler fügt im HTML-Head ein: <meta name=\"description\" content=\"Ihr Text hier\">",
            "impact":   "KI-Zitierbarkeit & Klickrate",
            "category": "KI-Zitierbarkeit & Inhalte",
        },
        {
            "name":     "Page Title vorhanden",
            "ok":       facts.get("title_ok", False),
            "detail":   f'"{facts["page_title"][:50]}…"' if facts.get("title_ok") else "Fehlt",
            "quickwin": "Page Title fehlt oder ist unzureichend — der Seitentitel ist Ihre 'Visitenkarte' für KI-Systeme.",
            "howto":    "Der Seitentitel sollte Ihren Betriebsnamen, den Ort und Ihr Alleinstellungsmerkmal enthalten. Beispiel: 'Hotel Alpenstern Kitzbühel | 4-Sterne Wellness & Ski'. Maximum 60 Zeichen. Bei WordPress: Den Titel im Yoast SEO Plugin bearbeiten. Bei anderen Systemen: Im HTML-Head den <title>-Tag anpassen. Jede Seite braucht einen eigenen, einzigartigen Titel!",
            "impact":   "KI-Zitierbarkeit & Auffindbarkeit",
            "category": "KI-Zitierbarkeit & Inhalte",
        },
        {
            "name":     "H1-Überschrift vorhanden",
            "ok":       facts.get("h1_ok", False),
            "detail":   (f'"{facts["h1_text"][:50]}…"' if facts.get("h1_ok")
                         else (f'{facts.get("h1_count", 0)} H1-Tags gefunden (genau 1 empfohlen)' if facts.get("h1_count", 0) > 1
                               else "Keine H1-Überschrift gefunden")),
            "quickwin": "Die H1-Überschrift ist die 'Hauptüberschrift' Ihrer Seite — KI-Systeme nutzen sie, um den Kerninhalt zu erkennen.",
            "howto":    "Jede Seite braucht genau eine H1-Überschrift (die größte Überschrift). Sie sollte klar beschreiben, worum es auf der Seite geht. Beispiel für die Startseite: 'Willkommen im Hotel Alpenstern — Ihr 4-Sterne Wellnesshotel in Kitzbühel'. Bei WordPress: Die erste Überschrift im Editor als 'Überschrift 1' formatieren. Wichtig: Nur EINE H1 pro Seite, weitere Überschriften als H2 oder H3.",
            "impact":   "Inhaltsstruktur & KI-Verständnis",
            "category": "KI-Zitierbarkeit & Inhalte",
        },
        # (Textsubstanz der Startseite wird jetzt von Signal 3 geprüft,
        #  Schema.org/JSON-LD inkl. Lodging-Entität von Signal 2 — siehe Ampel oben)
        # ── SECTION: Social & Sharing ──
        {
            "name":     "Open Graph Tags (og:title, og:description, og:image)",
            "ok":       facts.get("og_ok", False),
            "detail":   f'Gefunden: {", ".join(og_found)}' if og_found else "Keine OG-Tags gefunden",
            "quickwin": "Open Graph Tags fehlen — diese steuern, wie Ihr Betrieb auf Social Media UND in KI-Systemen dargestellt wird.",
            "howto":    "Open Graph Tags bestimmen Titel, Beschreibung und Vorschaubild, wenn jemand Ihre Website auf Facebook, WhatsApp oder LinkedIn teilt — und KI-Systeme nutzen sie ebenfalls. Bei WordPress: Yoast SEO → unter jeder Seite den Tab 'Social' öffnen und Titel, Beschreibung und Bild eintragen. Ohne WordPress: Ihr Webentwickler fügt im HTML-Head ein: og:title (Betriebsname), og:description (kurze Beschreibung), og:image (ein ansprechendes Foto, mind. 1200×630 Pixel).",
            "impact":   "KI-Kontext & Social Sharing",
            "category": "Social & Sharing",
        },
        # ── SECTION: Sprache & International ──
        {
            "name":     "Sprach-Attribut (lang=)",
            "ok":       facts.get("lang_ok", False),
            "detail":   f'lang="{facts["lang"]}"' if facts.get("lang_ok") else "Fehlt",
            "quickwin": "Sprach-Attribut fehlt — KI-Systeme wissen nicht, in welcher Sprache Ihre Seite geschrieben ist.",
            "howto":    "Das Sprach-Attribut ist eine kleine Ergänzung ganz am Anfang Ihres HTML-Codes. Ihr Webentwickler muss nur sicherstellen, dass der HTML-Tag so aussieht: <html lang=\"de\"> (für Deutsch) oder <html lang=\"de-AT\"> (für österreichisches Deutsch). Bei WordPress: Die meisten Themes setzen das automatisch — prüfen Sie unter Einstellungen → Allgemein, ob die richtige Sprache eingestellt ist.",
            "impact":   "Sprachliche Einordnung",
            "category": "Sprache & International",
        },
        {
            "name":     "Hreflang-Tags (Mehrsprachigkeit)",
            "ok":       facts.get("hreflang_ok", False),
            "detail":   f'Sprachen: {", ".join(facts.get("hreflang_langs", []))}' if facts.get("hreflang_ok") else "Keine Hreflang-Tags — nur einsprachig",
            "quickwin": "Hreflang-Tags fehlen — für internationale Gäste wissen KI-Systeme nicht, ob es Ihre Seite in anderen Sprachen gibt.",
            "howto":    "Hreflang-Tags sind relevant, wenn Sie Ihre Website in mehreren Sprachen anbieten (z.B. Deutsch + Englisch). Sie signalisieren KI-Systemen: 'Diese Seite gibt es auch auf Englisch unter dieser URL.' Bei WordPress: Das Plugin 'WPML' oder 'Polylang' setzt Hreflang-Tags automatisch. Falls Ihre Website nur auf Deutsch existiert und Sie keine internationalen Gäste ansprechen, ist dieser Punkt weniger wichtig — aber für Tourismusbetriebe mit internationaler Kundschaft sehr empfohlen.",
            "impact":   "Internationale KI-Sichtbarkeit",
            "category": "Sprache & International",
        },
        # ── SECTION: Barrierefreiheit & Medien ──
        {
            "name":     "Bilder mit Alt-Texten (min. 80%)",
            "ok":       facts.get("img_alt_ok", True),
            "detail":   f'{img_alt} von {img_total} Bildern mit Alt-Text ({img_pct}%)' if img_total > 0 else "Keine Bilder gefunden",
            "quickwin": f"Alt-Texte für Bilder ergänzen ({img_pct}% vorhanden) — KI-Systeme können Bilder ohne Beschreibung nicht 'sehen'.",
            "howto":    "Alt-Texte sind kurze Beschreibungen, die jedem Bild zugeordnet werden. Beispiel: Statt leer → 'Panoramablick vom Balkon des Hotel Alpenstern auf die Kitzbüheler Alpen'. Bei WordPress: Klicken Sie auf ein Bild in der Mediathek und füllen Sie das Feld 'Alternativer Text' aus. Beschreiben Sie, was auf dem Bild zu sehen ist — kurz, sachlich, mit Ortsbezug. Das hilft nicht nur KI-Systemen, sondern auch sehbehinderten Gästen und verbessert Ihre Barrierefreiheit.",
            "impact":   "KI-Bildverständnis & Barrierefreiheit",
            "category": "Barrierefreiheit & Medien",
        },
    ]


# Bewertet wird mit der Ampel der Signal-Module (GRÜN/GELB/ROT/UNBEKANNT),
# nicht mehr mit einem Punkte-Score. Logik: signals/__init__.py + befund.py.
ANZAHL_ZUSATZ_CHECKS = 14


# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
  <div class="brand-tag">TÜV-zertifizierter KI-Trainer · DACH Tourismus</div>
  <h1>🏔 GEO-Readiness <span>Checker</span></h1>
  <p>Wie sichtbar ist Ihr Betrieb in ChatGPT, Perplexity und Google AI?<br>
  Kostenlose Analyse mit GEO-Ampel — Ihr Kurz-Befund kommt als PDF per E-Mail.</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# FORMULAR
# ══════════════════════════════════════════════════════

if not st.session_state["analyse_done"]:
    st.subheader("Ihren Betrieb analysieren")

    col1, col2 = st.columns(2)
    with col1:
        betrieb = st.text_input("Name des Betriebs *", placeholder="z.B. Hotel Alpenstern")
        ort     = st.text_input("Ort / Destination *",  placeholder="z.B. St. Anton am Arlberg")
    with col2:
        website = st.text_input("Website-URL *", placeholder="https://www.hotel-alpenstern.at")
        typ     = st.selectbox("Betriebstyp *", [
            "Hotel (3–4 Sterne)", "Hotel (5 Sterne / Luxus)",
            "Pension / Gasthof", "Ferienwohnung / Appartement",
            "Ferienhaus / Chalet", "Boutique Hotel",
            "Wellnesshotel", "Tourismusverband / DMO", "Sonstiges"
        ])

    email = st.text_input(
        "Ihre E-Mail-Adresse * (für weiterführende Tipps)",
        placeholder="max@muster.at"
    )

    st.caption("* Pflichtfelder — Ihre Daten werden vertraulich behandelt und nicht an Dritte weitergegeben.")

    if st.button("🔍 Kostenlose GEO-Analyse starten", type="primary", use_container_width=True):
        fehler = []
        if not betrieb.strip(): fehler.append("Bitte Betriebsnamen eingeben.")
        if not ort.strip():     fehler.append("Bitte Ort eingeben.")
        if not website.strip(): fehler.append("Bitte Website-URL eingeben.")
        if not email.strip() or "@" not in email: fehler.append("Bitte gültige E-Mail eingeben.")

        if fehler:
            for f in fehler: st.error(f)
        else:
            if not website.startswith("http"):
                website = "https://" + website

            status = st.empty()
            domain = urlparse(website).netloc or website

            status.info("🔍 Signal 1/3: KI-Zugang (robots.txt) wird geprüft…")
            s1 = check_robots(domain)
            status.info("🔍 Signal 2/3: Strukturierte Betriebsdaten (Schema.org)…")
            s2 = check_schema(domain)
            status.info("🔍 Signal 3/3: Maschinenlesbarkeit der Startseite…")
            s3 = check_rendering(domain)
            befund = baue_befund(s1, s2, s3)

            status.info("🔍 Ergänzende technische Checkpunkte…")
            facts  = check_website(website)
            checks = build_checks(facts)

            status.info("📄 Kurz-Befund-PDF wird erstellt…")
            lead = {
                "betrieb": betrieb, "ort": ort, "email": email,
                "website": website, "typ": typ,
            }
            pdf_bytes = erzeuge_kurzbefund_pdf(lead, befund)

            status.info("📧 Kurz-Befund wird per E-Mail versendet…")
            mail_ok, mail_info = sende_kurzbefund(lead, befund, pdf_bytes,
                                                  secrets=st.secrets)

            status.info("🔍 Lead speichern…")
            lead_sheet = {
                **lead,
                "ampel":   befund["overall"],
                "signale": signal_kurzzeile(befund),
                "versand": ("versendet" if mail_ok else f"NICHT versendet: {mail_info}"),
            }
            write_lead_to_sheet(lead_sheet)
            st.session_state["leads"].append({
                **lead_sheet,
                "datum": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            })

            st.session_state["result"] = {
                "befund":    befund,
                "checks":    checks,
                "bots":      [{"name": b.name, "klasse": b.klasse,
                               "allowed": b.allowed, "beleg": b.beleg}
                              for b in s1.bots],
                "pdf_bytes": pdf_bytes,
                "mail_ok":   mail_ok,
                "mail_info": mail_info,
            }
            st.session_state["lead_data"]    = lead
            st.session_state["analyse_done"] = True
            status.success("✅ Analyse abgeschlossen!")
            time.sleep(0.3)
            status.empty()
            st.rerun()


# ══════════════════════════════════════════════════════
# ERGEBNIS
# ══════════════════════════════════════════════════════

if st.session_state["analyse_done"] and st.session_state["result"]:
    result    = st.session_state["result"]
    lead_data = st.session_state["lead_data"]
    befund    = result["befund"]
    checks    = result["checks"]

    # Ampel-Karte (statt Punkte-Score)
    st.markdown(f"""
    <div class="ampel-card" style="background:{befund['farbe']}">
      <div class="ampel-status">{befund['symbol']} {befund['overall']}</div>
      <div class="ampel-label">GEO-Ampel · KI-Sichtbarkeit Ihres Betriebs</div>
      <div class="ampel-klartext">{befund['klartext']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Die drei Signale im Detail
    st.subheader("🚦 Die drei Prüfbereiche")
    signal_html = []
    for s in befund["signale"]:
        farbe = AMPEL_FARBEN[s["status"]]
        signal_html.append(
            f'<div class="signal-card" style="border-left:4px solid {farbe}">'
            f'<span class="signal-status" style="background:{farbe}">{s["status"]}</span>'
            f'<span class="signal-name">{s["name"]}</span>'
            f'<div class="signal-grund">{s["grund"]}</div>'
            f'</div>'
        )
    st.markdown("\n".join(signal_html), unsafe_allow_html=True)

    # PDF- und Versand-Status
    if result.get("mail_ok"):
        st.success(f"📧 Ihr Kurz-Befund wurde als PDF an **{lead_data['email']}** gesendet.")
        if result.get("mail_info"):
            st.caption(result["mail_info"])
    else:
        st.info("📄 Der E-Mail-Versand ist derzeit nicht möglich — "
                "laden Sie Ihren Kurz-Befund einfach hier herunter.")
    st.download_button(
        "📥 Kurz-Befund als PDF herunterladen",
        data=result["pdf_bytes"],
        file_name=f"GEO-Kurz-Befund_{lead_data['betrieb'].replace(' ', '_')}.pdf",
        mime="application/pdf",
    )

    # Ergänzende Checkpunkte — single HTML block to prevent React DOM conflicts
    st.subheader(f"🔬 {ANZAHL_ZUSATZ_CHECKS} Ergänzende technische Checkpunkte")
    passed = sum(1 for c in checks if c["ok"])
    st.caption(f"{passed} von {ANZAHL_ZUSATZ_CHECKS} Checkpunkten bestanden")

    checks_html_parts = []
    categories_seen = []
    for c in checks:
        cat = c.get("category", "")
        if cat and cat not in categories_seen:
            categories_seen.append(cat)
            checks_html_parts.append(f'<div class="category-header">{cat}</div>')
        css  = "check-ok" if c["ok"] else "check-fail"
        icon = "✅" if c["ok"] else "❌"
        checks_html_parts.append(
            f'<div class="{css}">'
            f'<div class="check-name">{icon} {c["name"]}</div>'
            f'<div class="check-detail">{c["detail"]}</div>'
            f'</div>'
        )
    st.markdown("\n".join(checks_html_parts), unsafe_allow_html=True)

    # KI-Bot Detail (aus Signal 1: 13 Bots in Klasse A/B, mit Beleg-Zeile)
    bots_html_parts = []
    for b in result.get("bots", []):
        klasse = "sichtbarkeitskritisch" if b["klasse"] == "A" else "Trainings-Bot"
        if b["allowed"]:
            bots_html_parts.append(f'<div class="robots-allowed">✅ <strong>{b["name"]}</strong> ({klasse}) — darf lesen · {b["beleg"]}</div>')
        else:
            bots_html_parts.append(f'<div class="robots-blocked">❌ <strong>{b["name"]}</strong> ({klasse}) — blockiert · {b["beleg"]}</div>')
    if bots_html_parts:
        with st.expander("🤖 KI-Bot Crawlability im Detail"):
            st.markdown("\n".join(bots_html_parts), unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # HANDLUNGSEMPFEHLUNGEN — actionable recommendations
    # ══════════════════════════════════════════════════════
    failed = [c for c in checks if not c["ok"]]

    if befund["empfehlungen"] or failed:
        st.subheader("📋 Handlungsempfehlungen für Ihren Betrieb")
        st.markdown("Basierend auf der Analyse ergeben sich folgende **konkrete Maßnahmen**, "
                    "priorisiert nach Wirkung auf Ihre KI-Sichtbarkeit:")

    if befund["empfehlungen"]:
        st.markdown("##### 🚦 Aus den drei Prüfbereichen (höchste Priorität)")
        empf_html = "".join(
            f'<div class="quickwin-card qw-hoch">'
            f'<div class="qw-titel">{i}. {e}</div>'
            f'</div>'
            for i, e in enumerate(befund["empfehlungen"], 1)
        )
        st.markdown(empf_html, unsafe_allow_html=True)

    if failed:

        # Split failed checks into priority tiers
        critical = [c for c in failed if c["impact"] and ("kritisch" in c["impact"].lower() or "höchste" in c["impact"].lower() or "sehr hoch" in c["impact"].lower())]
        high     = [c for c in failed if c not in critical and failed.index(c) < 4]
        medium   = [c for c in failed if c not in critical and c not in high]

        def build_recommendation_html(c, css_class):
            return (
                f'<div class="quickwin-card {css_class}">'
                f'<div class="qw-titel">{c["name"]}</div>'
                f'<div class="qw-impact">💡 {c["quickwin"]}</div>'
                f'<div class="qw-impact" style="color:#999;margin-top:4px">Wirkung: {c["impact"]}</div>'
                f'</div>'
            )

        # Build all recommendation HTML in one block per priority tier
        reco_html = ""
        reco_expanders = []

        if critical:
            reco_html += '<h5>🔴 Sofort umsetzen (kritische Wirkung)</h5>'
            for c in critical:
                reco_html += build_recommendation_html(c, "qw-hoch")
                if c.get("howto"):
                    reco_expanders.append(c)

        if high:
            reco_html += '<h5>🟠 Kurzfristig umsetzen (hohe Wirkung)</h5>'
            for c in high:
                reco_html += build_recommendation_html(c, "qw-mittel")
                if c.get("howto"):
                    reco_expanders.append(c)

        if medium:
            reco_html += '<h5>🟡 Mittelfristig umsetzen (Feinschliff)</h5>'
            for c in medium:
                reco_html += build_recommendation_html(c, "qw-niedrig")
                if c.get("howto"):
                    reco_expanders.append(c)

        # Render all HTML cards in one block
        st.markdown(reco_html, unsafe_allow_html=True)

        # Render expanders separately (native widgets, not mixed with HTML)
        for c in reco_expanders:
            with st.expander(f"📖 So setzen Sie es um: {c['name']}"):
                st.markdown(c["howto"])

        # Summary action plan — richtet sich nach der Gesamt-Ampel
        st.markdown("---")
        st.markdown("##### 🎯 Zusammenfassung")
        total_failed = len(failed)
        if befund["overall"] == "GRÜN":
            summary = (f"Ihr Betrieb hat eine **gute technische Basis** für KI-Sichtbarkeit "
                       f"(Ampel GRÜN). Mit {total_failed} gezielten Optimierungen aus den "
                       f"ergänzenden Checkpunkten holen Sie den letzten Feinschliff heraus.")
        elif befund["overall"] == "GELB":
            summary = (f"Ihre GEO-Ampel steht auf **GELB**: {befund['klartext']} "
                       f"Beginnen Sie mit den Maßnahmen aus den drei Prüfbereichen — "
                       f"danach lohnen sich die {total_failed} ergänzenden Punkte.")
        elif befund["overall"] == "ROT":
            summary = (f"Ihre GEO-Ampel steht auf **ROT**: {befund['klartext']} "
                       f"Die Maßnahmen aus den drei Prüfbereichen haben Vorrang — "
                       f"ohne sie verpuffen alle weiteren Optimierungen.")
        else:
            summary = (f"Die automatische Prüfung war **nicht vollständig möglich** "
                       f"(Ampel UNBEKANNT). {befund['klartext']}")
        st.info(summary)
    elif not befund["empfehlungen"]:
        st.success(f"🎉 Ampel {befund['overall']} und alle {ANZAHL_ZUSATZ_CHECKS} ergänzenden "
                   "Checkpunkte bestanden! Ihr Betrieb ist hervorragend für KI-Sichtbarkeit aufgestellt.")

    # Verkaufs-Brücke: bei GELB/ROT konkretes Angebot, bei GRÜN weicher Hinweis
    if befund["verkaufsbruecke"]:
        st.markdown(f"""
        <div class="cta-box">
          <h3>Ihre Ampel steht auf {befund['overall']} — wir bringen sie auf GRÜN.</h3>
          <p>
            Das <strong>GEO-Optimierungspaket Professional (€ 149)</strong> setzt die oben
            genannten Maßnahmen in fertige, KI-lesbare Texte um: FAQ, Startseiten-Überschrift,
            USP-Box, lokale Keywords, Google-Business-Text, Meta-Descriptions und ein neuer
            „Über uns"-Text — geliefert innerhalb von 24 Stunden, ohne technisches Vorwissen.
          </p>
          <p style="font-size:13px;opacity:0.7;">Einmalig € 149 · kein Abo · Upgrade auf ReviewRadar möglich</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="cta-box">
          <h3>Ampel GRÜN — jetzt den Vorsprung ausbauen</h3>
          <p>
            Die Technik trägt. Der nächste Hebel sind Ihre Inhalte: Als TÜV-zertifizierter
            KI-Trainer mit 30+ Jahren Tourismus-Erfahrung im DACH-Raum helfe ich Ihnen,
            aus Sichtbarkeit auch Buchungen zu machen.
          </p>
          <p style="font-size:13px;opacity:0.7;">GEO-Optimierungspaket · ReviewRadar · Workshops & Beratung</p>
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🌐 gernot-riedel.com", "https://gernot-riedel.com", use_container_width=True)
    with col2:
        st.link_button("📧 Kontakt aufnehmen",
                       "mailto:kontakt@gernot-riedel.com?subject=GEO-Beratung%20Anfrage",
                       use_container_width=True)

    st.divider()
    if st.button("🔄 Neue Analyse starten"):
        st.session_state["analyse_done"] = False
        st.session_state["result"]       = None
        st.session_state["lead_data"]    = None
        st.rerun()


# ══════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════

st.divider()
with st.expander("🔒 Admin-Bereich"):
    if not st.session_state["admin_logged_in"]:
        pw = st.text_input("Passwort", type="password", key="admin_pw")
        if st.button("Anmelden", key="admin_login"):
            if pw == st.secrets.get("ADMIN_PASSWORD", ""):
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("Falsches Passwort.")
    else:
        st.success("✅ Admin-Zugang aktiv")
        leads = st.session_state.get("leads", [])
        if leads:
            st.write(f"**{len(leads)} Lead(s) in dieser Session:**")
            for i, l in enumerate(leads, 1):
                st.write(f"{i}. **{l['betrieb']}** ({l['ort']}) — Ampel {l.get('ampel','?')} ({l.get('signale','')}) — {l['email']} — {l.get('versand','')} — {l.get('datum','')}")
            out = io.StringIO()
            w   = csv.DictWriter(out, fieldnames=["datum","betrieb","ort","email","website","typ","ampel","signale","versand"])
            w.writeheader()
            w.writerows(leads)
            st.download_button("📥 CSV exportieren",
                               data=out.getvalue().encode("utf-8-sig"),
                               file_name=f"geo_leads_{datetime.date.today()}.csv",
                               mime="text/csv")
        else:
            st.info("Noch keine Leads in dieser Session.")

        st.markdown("---")
        st.markdown(f"🔗 [Alle Leads im Google Sheet öffnen](https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)")

        if st.button("🔓 Abmelden", key="admin_logout"):
            st.session_state["admin_logged_in"] = False
            st.rerun()


# ── FOOTER ──
st.markdown("""
<div class="footer-bar">
  <strong style="color:#c9a84c">Gernot Riedel Tourism Consulting</strong> &nbsp;|&nbsp;
  TÜV-zertifizierter KI-Trainer &nbsp;|&nbsp;
  kontakt@gernot-riedel.com &nbsp;|&nbsp;
  +43 676 7237811 &nbsp;|&nbsp;
  gernot-riedel.com
</div>
""", unsafe_allow_html=True)
