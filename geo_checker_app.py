import streamlit as st
import csv
import io
import datetime
import re
import time
import urllib.request
from urllib.parse import urlparse

import gspread
from google.oauth2.service_account import Credentials

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

.score-card {
    background:linear-gradient(135deg,#0d6248 0%,#1a7a5a 100%);
    border-radius:8px; padding:28px 32px; text-align:center; margin:20px 0; color:white;
}
.score-number { font-size:64px; font-weight:700; line-height:1; }
.score-label { font-size:14px; opacity:0.8; margin-top:4px; letter-spacing:1px; text-transform:uppercase; }
.score-interpretation { font-size:17px; font-weight:600; margin-top:12px; }

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

SHEET_ID  = "1bNBtr9w__zlPL_5XETHhewu3TZAc7qAR1wm8sRO5WVI"
SHEET_TAB = "Leads"

def get_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_TAB)

def write_lead_to_sheet(data: dict) -> bool:
    try:
        sheet = get_sheet()
        if sheet.row_count < 1 or sheet.cell(1, 1).value != "Datum":
            sheet.insert_row(
                ["Datum", "Betrieb", "Ort", "E-Mail", "Website", "Typ", "Score", "Max", "Score %"],
                index=1
            )
        sheet.append_row([
            datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            data.get("betrieb", ""),
            data.get("ort", ""),
            data.get("email", ""),
            data.get("website", ""),
            data.get("typ", ""),
            data.get("score", 0),
            MAX_SCORE,
            f"{round(data.get('score', 0) / MAX_SCORE * 100)}%",
        ])
        return True
    except Exception as e:
        st.warning(f"Google Sheets: {e}")
        return False


# ══════════════════════════════════════════════════════
# TECHNISCHE MESSUNG
# ══════════════════════════════════════════════════════

def check_website(url: str) -> dict:
    """Misst alle 18 technischen GEO- und KI-Readiness-Faktoren direkt und verifizierbar."""
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    facts  = {"https": parsed.scheme == "https"}

    # robots.txt
    robots_text = ""
    try:
        req = urllib.request.Request(
            f"{base}/robots.txt", headers={"User-Agent": "GEO-Checker/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            robots_text = resp.read().decode("utf-8", errors="ignore")
        facts["robots_exists"] = True
    except Exception:
        facts["robots_exists"] = False

    # KI-Bot Crawlability
    AI_BOTS = {
        "GPTBot":          "OpenAI / ChatGPT",
        "ClaudeBot":       "Anthropic / Claude",
        "PerplexityBot":   "Perplexity",
        "Google-Extended": "Google AI (Gemini)",
        "Bytespider":      "TikTok / ByteDance",
    }
    blocked_bots, allowed_bots = [], []
    if robots_text:
        lines, current_ua, disallows = robots_text.lower().split("\n"), None, {}
        for line in lines:
            line = line.strip()
            if line.startswith("user-agent:"):
                current_ua = line.replace("user-agent:", "").strip()
                disallows.setdefault(current_ua, [])
            elif line.startswith("disallow:") and current_ua:
                disallows[current_ua].append(line.replace("disallow:", "").strip())
        for bot, label in AI_BOTS.items():
            bl = bot.lower()
            blocked = (bl in disallows and ("/" in disallows[bl] or "" in disallows[bl])) or \
                      ("*" in disallows and "/" in disallows["*"])
            (blocked_bots if blocked else allowed_bots).append({"bot": bot, "label": label})
    else:
        allowed_bots = [{"bot": b, "label": l} for b, l in AI_BOTS.items()]

    facts["blocked_bots"] = blocked_bots
    facts["allowed_bots"] = allowed_bots

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
    """Erstellt die 18 Checkpunkte mit Ergebnis und Quick-Win-Hinweis."""
    bots_ok = len(facts.get("blocked_bots", [])) == 0

    # Image alt text detail
    img_total = facts.get("img_total", 0)
    img_alt   = facts.get("img_with_alt", 0)
    img_pct   = facts.get("img_alt_pct", 100)

    # JSON-LD detail
    jsonld_types = facts.get("jsonld_types", [])
    jsonld_detail = f'{facts.get("jsonld_count", 0)} Block(s)'
    if jsonld_types:
        jsonld_detail += f' — Typen: {", ".join(jsonld_types[:5])}'

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
        {
            "name":     "robots.txt — KI-Bots erlaubt",
            "ok":       bots_ok,
            "detail":   "Alle KI-Bots erlaubt" if bots_ok else f"{len(facts.get('blocked_bots',[]))} Bot(s) blockiert",
            "quickwin": "robots.txt anpassen — GPTBot, ClaudeBot, PerplexityBot und Google-Extended müssen crawlen dürfen.",
            "howto":    "Die robots.txt ist eine einfache Textdatei im Hauptverzeichnis Ihrer Website. Bitten Sie Ihren Webentwickler, folgende Einträge NICHT zu blockieren: GPTBot, ClaudeBot, PerplexityBot, Google-Extended. Konkret bedeutet das: Es darf KEIN 'Disallow: /' für diese Bots stehen. Falls Sie unsicher sind, schicken Sie Ihrem Webentwickler einfach diesen Check-Bericht.",
            "impact":   "KI-Sichtbarkeit direkt",
            "category": "Crawlbarkeit & Indexierung",
        },
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
        {
            "name":     "Ausreichend Textinhalt (min. 300 Wörter)",
            "ok":       facts.get("content_ok", False),
            "detail":   f'{facts.get("word_count", 0)} Wörter gefunden' if facts.get("content_ok") else f'Nur {facts.get("word_count", 0)} Wörter — zu wenig für KI-Extraktion',
            "quickwin": "Ihre Startseite hat zu wenig Text — KI-Systeme können Ihren Betrieb nicht ausreichend beschreiben.",
            "howto":    "KI-Systeme wie ChatGPT brauchen genug Text, um Ihren Betrieb verstehen und empfehlen zu können. Ergänzen Sie auf der Startseite: (1) Eine kurze Betriebsbeschreibung (wer Sie sind, was Sie besonders macht). (2) Ihre wichtigsten Angebote (Zimmer, Wellness, Gastronomie). (3) Lage und Umgebung (was kann man bei Ihnen erleben?). (4) Warum Gäste Sie wählen sollten. Ziel: Mindestens 300 Wörter echten, informativen Text — keine Füllwörter, sondern Fakten und Beschreibungen.",
            "impact":   "KI-Verständnis & Empfehlungsqualität",
            "category": "KI-Zitierbarkeit & Inhalte",
        },
        # ── SECTION: Strukturierte Daten ──
        {
            "name":     "Schema.org Markup",
            "ok":       facts.get("schema_org", False),
            "detail":   "Gefunden" if facts.get("schema_org") else "Nicht gefunden",
            "quickwin": "Schema.org Markup fehlt — das ist die 'Maschinensprache', mit der KI-Systeme Ihre Daten lesen.",
            "howto":    "Strukturierte Daten sagen KI-Systemen exakt: 'Das ist ein Hotel, es liegt hier, hat diese Sterne, diese Preise.' Bei WordPress: Installieren Sie das Plugin 'Schema Pro' oder 'Rank Math' (hat Schema-Funktion integriert). Wählen Sie als Typ 'Hotel' oder 'LodgingBusiness' und füllen Sie Name, Adresse, Telefon, Sternekategorie und Preisspanne aus. Ohne WordPress: Ihr Webentwickler kann ein JSON-LD Script im HTML-Head einfügen — fragen Sie nach 'Hotel Schema Markup'.",
            "impact":   "KI-Zitierbarkeit — höchste Priorität",
            "category": "Strukturierte Daten",
        },
        {
            "name":     "JSON-LD Structured Data",
            "ok":       facts.get("jsonld_ok", False),
            "detail":   jsonld_detail if facts.get("jsonld_ok") else "Kein JSON-LD gefunden",
            "quickwin": "JSON-LD ist das bevorzugte Datenformat — Google, ChatGPT und Perplexity lesen es am zuverlässigsten.",
            "howto":    "JSON-LD ist ein unsichtbarer Code-Block im HTML Ihrer Seite, der Ihre Betriebsdaten maschinenlesbar macht. Es ist das Format, das Google offiziell empfiehlt. Bei WordPress: Rank Math oder Schema Pro erzeugen automatisch JSON-LD. Manuell: Nutzen Sie den Google Structured Data Markup Helper (Google-Suche danach), um den Code zu erzeugen, und lassen Sie ihn von Ihrem Webentwickler im HTML-Head einfügen. Enthaltene Infos: Betriebsname, Adresse, Telefon, Öffnungszeiten, Bewertungen, Preise.",
            "impact":   "KI-Datenextraktion — sehr hoch",
            "category": "Strukturierte Daten",
        },
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


MAX_SCORE = 36  # 18 checks × 2 points

def score_farbe(s: int) -> str:
    if s >= 28: return "#27ae60"
    if s >= 18: return "#e67e22"
    return "#c0392b"

def score_interpretation(s: int) -> str:
    if s >= 30: return "🟢 Sehr gute GEO- & KI-Basis — Inhalte weiter optimieren"
    if s >= 22: return "🟡 Solide Basis — einige technische Lücken schließen"
    if s >= 12: return "🟠 Technische Schwächen — KI-Sichtbarkeit stark eingeschränkt"
    return "🔴 Kritisch — grundlegende technische Voraussetzungen fehlen"


# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
  <div class="brand-tag">TÜV-zertifizierter KI-Trainer · DACH Tourismus</div>
  <h1>🏔 GEO-Readiness <span>Checker</span></h1>
  <p>Wie sichtbar ist Ihr Betrieb in ChatGPT, Perplexity und Google AI?<br>
  Kostenlose technische Analyse in 30 Sekunden — 18 verifizierte Checkpunkte.</p>
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
            status.info("🔍 Website wird analysiert… (ca. 15–30 Sekunden)")
            facts = check_website(website)
            status.info("🔍 Ergebnisse auswerten…")
            checks = build_checks(facts)
            score  = sum(2 for c in checks if c["ok"])
            status.info("🔍 Lead speichern…")

            lead = {
                "betrieb": betrieb, "ort": ort, "email": email,
                "website": website, "typ": typ, "score": score,
            }
            write_lead_to_sheet(lead)
            st.session_state["leads"].append({
                **lead,
                "datum": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            })

            st.session_state["result"] = {
                "checks":       checks,
                "score":        score,
                "blocked_bots": facts.get("blocked_bots", []),
                "allowed_bots": facts.get("allowed_bots", []),
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
    score     = result["score"]
    checks    = result["checks"]

    # Score-Karte
    pct = round(score / MAX_SCORE * 100)
    st.markdown(f"""
    <div class="score-card">
      <div class="score-number" style="color:{score_farbe(score)}">{score}</div>
      <div class="score-label">von {MAX_SCORE} Punkten · {pct}% erreicht</div>
      <div class="score-interpretation">{score_interpretation(score)}</div>
    </div>
    """, unsafe_allow_html=True)

    # Checkpunkte — grouped by category
    st.subheader("🔬 18 Gemessene GEO- & KI-Checkpunkte")
    passed = sum(1 for c in checks if c["ok"])
    st.caption(f"{passed} von 18 Checkpunkten bestanden")

    categories_seen = []
    for c in checks:
        cat = c.get("category", "")
        if cat and cat not in categories_seen:
            categories_seen.append(cat)
            st.markdown(f"**{cat}**")
        css  = "check-ok" if c["ok"] else "check-fail"
        icon = "✅" if c["ok"] else "❌"
        st.markdown(f"""
        <div class="{css}">
          <div class="check-name">{icon} {c['name']}</div>
          <div class="check-detail">{c['detail']}</div>
        </div>
        """, unsafe_allow_html=True)

    # KI-Bot Detail
    with st.expander("🤖 KI-Bot Crawlability im Detail"):
        for b in result.get("blocked_bots", []):
            st.markdown(f'<div class="robots-blocked">❌ <strong>{b["bot"]}</strong> ({b["label"]}) — blockiert in robots.txt</div>', unsafe_allow_html=True)
        for a in result.get("allowed_bots", []):
            st.markdown(f'<div class="robots-allowed">✅ <strong>{a["bot"]}</strong> ({a["label"]}) — darf crawlen</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # HANDLUNGSEMPFEHLUNGEN — actionable recommendations
    # ══════════════════════════════════════════════════════
    failed = [c for c in checks if not c["ok"]]

    if failed:
        st.subheader("📋 Handlungsempfehlungen für Ihren Betrieb")
        st.markdown("Basierend auf der Analyse ergeben sich folgende **konkrete Maßnahmen**, "
                    "priorisiert nach Wirkung auf Ihre KI-Sichtbarkeit:")

        # Split failed checks into priority tiers
        critical = [c for c in failed if c["impact"] and ("kritisch" in c["impact"].lower() or "höchste" in c["impact"].lower() or "sehr hoch" in c["impact"].lower())]
        high     = [c for c in failed if c not in critical and failed.index(c) < 4]
        medium   = [c for c in failed if c not in critical and c not in high]

        def render_recommendation(c, css_class):
            st.markdown(f"""
            <div class="quickwin-card {css_class}">
              <div class="qw-titel">{c['name']}</div>
              <div class="qw-impact">💡 {c['quickwin']}</div>
              <div class="qw-impact" style="color:#999;margin-top:4px">Wirkung: {c['impact']}</div>
            </div>
            """, unsafe_allow_html=True)
            if c.get("howto"):
                with st.expander(f"📖 So setzen Sie es um: {c['name']}"):
                    st.markdown(c["howto"])

        if critical:
            st.markdown("##### 🔴 Sofort umsetzen (kritische Wirkung)")
            for c in critical:
                render_recommendation(c, "qw-hoch")

        if high:
            st.markdown("##### 🟠 Kurzfristig umsetzen (hohe Wirkung)")
            for c in high:
                render_recommendation(c, "qw-mittel")

        if medium:
            st.markdown("##### 🟡 Mittelfristig umsetzen (Feinschliff)")
            for c in medium:
                render_recommendation(c, "qw-niedrig")

        # Summary action plan
        st.markdown("---")
        st.markdown("##### 🎯 Zusammenfassung")
        total_failed = len(failed)
        if pct >= 70:
            summary = (f"Ihr Betrieb hat bereits eine **gute Basis** für KI-Sichtbarkeit. "
                       f"Mit {total_failed} gezielten Optimierungen können Sie Ihre "
                       f"Auffindbarkeit in ChatGPT, Perplexity und Google AI weiter steigern.")
        elif pct >= 40:
            summary = (f"Ihr Betrieb hat **Nachholbedarf** bei {total_failed} Checkpunkten. "
                       f"Die wichtigsten Maßnahmen betreffen {', '.join(set(c.get('category','') for c in failed[:3]))}. "
                       f"Ohne diese Optimierungen bleibt Ihr Betrieb für KI-Systeme weitgehend unsichtbar.")
        else:
            summary = (f"Ihr Betrieb ist aktuell **kaum sichtbar** für KI-Systeme. "
                       f"{total_failed} von 18 Checkpunkten müssen adressiert werden. "
                       f"Wir empfehlen dringend, mit den kritischen Maßnahmen zu beginnen, "
                       f"um die technische Grundlage für KI-Sichtbarkeit zu schaffen.")
        st.info(summary)
    else:
        st.success("🎉 Alle 18 technischen Checkpunkte bestanden! Ihr Betrieb ist hervorragend für KI-Sichtbarkeit aufgestellt.")

    # CTA
    st.markdown("""
    <div class="cta-box">
      <h3>Möchten Sie mehr aus Ihrem Score herausholen?</h3>
      <p>
        Als TÜV-zertifizierter KI-Trainer mit 30+ Jahren Tourismus-Erfahrung im DACH-Raum
        helfe ich Ihnen, Ihren Betrieb in ChatGPT, Perplexity und Google AI sichtbar zu machen —
        mit fertigen Texten, konkreten Maßnahmen und ohne technisches Vorwissen.
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
                st.write(f"{i}. **{l['betrieb']}** ({l['ort']}) — {l['score']}/{MAX_SCORE} Pkt — {l['email']} — {l.get('datum','')}")
            out = io.StringIO()
            w   = csv.DictWriter(out, fieldnames=["datum","betrieb","ort","email","website","typ","score"])
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
