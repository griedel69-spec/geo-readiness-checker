#!/bin/bash
mkdir -p .streamlit

cat > .streamlit/secrets.toml << SECRETS_EOF
ADMIN_PASSWORD = "${ADMIN_PASSWORD}"

# E-Mail-Versand (Kurz-Befund-PDF + Benachrichtigung an Gernot).
# Ohne diese Werte laeuft die App trotzdem — dann nur PDF-Download statt Mail.
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

streamlit run geo_checker_app.py \
  --server.port=${PORT:-10000} \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
