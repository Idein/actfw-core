#!/bin/sh
# Run as root immediately after checkout, before downloading CI tools.
set -eu
sed -i \
    -e 's|^mozilla/emSign_ECC_Root_CA_-_G3\\.crt$|!&|' \
    -e 's|^mozilla/Comodo_AAA_Services_root\\.crt$|!&|' \
    /etc/ca-certificates.conf
update-ca-certificates --fresh
# Python/Requests and curl may otherwise select a separate bundle.
if [ -n "${BASH_ENV:-}" ]; then
    cat >> "$BASH_ENV" <<'ENV'
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV
fi
