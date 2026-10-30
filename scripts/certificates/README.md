Public certificates for offline CA regression checks. No private keys are included.

The intermediate fingerprints are documented in Mozilla incident 2083449, comment 2:
https://bugzilla.mozilla.org/show_bug.cgi?id=2083449#c2
Amazon Root CA 1 is the positive control, extracted from certifi 2026.10.19.
Tests use a fixed date and require issuer/self-signed errors, rather than expiry errors.
