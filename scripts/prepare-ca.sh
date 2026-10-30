#!/bin/sh
# Run as root immediately after checkout, before downloading CI tools.
set -eu
# Debian and Raspbian use different names for the AAA root. Match certificate
# fingerprints so a renamed root is disabled as well.
for certificate in /usr/share/ca-certificates/mozilla/*.crt; do
    fingerprint=$(openssl x509 -in "$certificate" -noout -fingerprint -sha256)
    fingerprint=$(printf '%s' "${fingerprint#*=}" | tr -d ':' | tr '[:upper:]' '[:lower:]')
    case "$fingerprint" in
        86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b|d7a7a0fb5d7e2731d771e9484ebcdef71d5f0c3e0a2948782bc83ee0ea699ef4)
            relative=${certificate#/usr/share/ca-certificates/}
            sed -i "s|^$relative$|!&|" /etc/ca-certificates.conf
            ;;
    esac
done
update-ca-certificates --fresh
# Python/Requests and curl may otherwise select a separate bundle.
if [ -n "${BASH_ENV:-}" ]; then
    cat >> "$BASH_ENV" <<'ENV'
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV
fi
