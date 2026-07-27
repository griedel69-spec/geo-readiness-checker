#!/bin/bash
mkdir -p .streamlit

cat > .streamlit/secrets.toml << SECRETS_EOF
ADMIN_PASSWORD = "${ADMIN_PASSWORD}"

# E-Mail-Versand (Kurz-Befund-PDF + Benachrichtigung an Gernot).
# Bevorzugter Weg: Brevo-Web-API (Render blockt direkte SMTP-Verbindungen).
# Ohne diese Werte laeuft die App trotzdem — dann nur PDF-Download statt Mail.
BREVO_API_KEY = "${BREVO_API_KEY}"
SMTP_HOST = "${SMTP_HOST}"
SMTP_PORT = "${SMTP_PORT:-587}"
SMTP_USER = "${SMTP_USER}"
SMTP_PASS = "${SMTP_PASS}"
MAIL_FROM = "${MAIL_FROM}"
NOTIFY_EMAIL = "${NOTIFY_EMAIL:-kontakt@gernot-riedel.com}"

[gcp_service_account]
${GCP_SERVICE_ACCOUNT_TOML}
SECRETS_EOF

echo "secrets.toml geschrieben"

# GEO-Fix: Streamlit liefert im rohen HTML nur ein leeres Geruest
# (<title>Streamlit</title>, "You need to enable JavaScript to run this app.") -
# fuer Nicht-JS-Crawler unsichtbar. Ergaenzt Titel, Meta-Description, Canonical-Link
# und einen inhaltlich echten Noscript-Fallback (Kontakt laut Impressum). Ersetzt
# NICHT die interaktive Pruefung selbst - die bleibt zwingend JavaScript-abhaengig.
python3 - <<'PATCH_EOF'
import os
import re
import streamlit

index_path = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")
with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

MARKER = "<!-- geo-radar-seo-patch -->"
if MARKER in html:
    print("index.html bereits gepatcht, ueberspringe.")
else:
    head_addition = (
        MARKER
        + "<title>GEO-Readiness Check für Hotels | Gernot Riedel</title>"
        + '<meta name="description" content="Kostenloser GEO-Readiness Check: '
        "prüfen Sie in rund 30 Sekunden, ob KI-Systeme wie ChatGPT, Perplexity "
        'und Google AI Ihr Hotel finden, lesen und korrekt zuordnen können.">'
        + '<link rel="canonical" href="https://gernot-riedel.com/geo-readiness-check-hotel/">'
    )
    html, n_title = re.subn(r"<title>[^<]*</title>", head_addition, html, count=1)

    noscript_text = (
        "GEO-Readiness Check für Hotels — kostenloser KI-Sichtbarkeits-Check von "
        "Gernot Riedel, Unternehmensberatung. Dieses Tool prüft in rund 30 Sekunden, "
        "ob KI-Systeme wie ChatGPT, Perplexity und Google AI Ihr Hotel oder Ihre Pension "
        "finden, lesen und korrekt zuordnen können. Geprüft werden drei Kernbereiche: "
        "der KI-Crawler-Zugang (robots.txt), die strukturierten Betriebsdaten (Schema.org) "
        "und die Maschinenlesbarkeit der Startseite. Das Ergebnis erhalten Sie als GEO-Ampel "
        "(GRÜN, GELB oder ROT) sowie als Kurz-Befund per PDF per E-Mail. Für den "
        "interaktiven Check ist JavaScript im Browser erforderlich. Ohne JavaScript wenden "
        "Sie sich bitte direkt an uns: Gernot Riedel, Unternehmensberatung, Uferstraße 4, "
        "A-5751 Maishofen, Österreich. Telefon: +43 676 7237811. E-Mail: "
        "kontakt@gernot-riedel.com. Mehr Informationen: "
        "https://gernot-riedel.com/geo-readiness-check-hotel/"
    )
    html, n_noscript = re.subn(
        r"<noscript>.*?</noscript>",
        "<noscript>" + noscript_text + "</noscript>",
        html,
        count=1,
        flags=re.S,
    )

    if n_title and n_noscript:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("index.html gepatcht: Titel, Meta-Description, Canonical, Noscript-Fallback ergaenzt.")
    else:
        print(f"WARNUNG: index.html nicht wie erwartet aufgebaut (title-Treffer={n_title}, noscript-Treffer={n_noscript}) - ungepatcht weiter.")
PATCH_EOF

streamlit run geo_checker_app.py \
  --server.port=${PORT:-10000} \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
