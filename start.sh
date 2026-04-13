#!/bin/bash
mkdir -p .streamlit

cat > .streamlit/secrets.toml << SECRETS_EOF
ADMIN_PASSWORD = "${ADMIN_PASSWORD}"

[gcp_service_account]
${GCP_SERVICE_ACCOUNT_TOML}
SECRETS_EOF

echo "secrets.toml geschrieben"

streamlit run geo_checker_app.py \
  --server.port=${PORT:-10000} \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
