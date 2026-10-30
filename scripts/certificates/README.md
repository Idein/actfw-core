Public certificates for offline CA regression checks. No private keys are included.

The two roots and six Sectigo-cross-signed TLS intermediates are copied from
Idein/actcast-device-api tests/certificates at commit 7c18c05197c36ed31e73b2927a50cea048e13e2e.
The intermediate fingerprints are documented in Mozilla incident 2083449, comment 2:
https://bugzilla.mozilla.org/show_bug.cgi?id=2083449#c2
Amazon Root CA 1 is the positive control, extracted from certifi 2026.10.19.
Tests use a fixed date and require issuer/self-signed errors, rather than expiry errors.
