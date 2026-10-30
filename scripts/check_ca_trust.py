"""Check the OS and optional certifi stores using public certificate fixtures."""
import argparse
import hashlib
import re
import ssl
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

BAD_ROOTS = {
    "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b",
    "d7a7a0fb5d7e2731d771e9484ebcdef71d5f0c3e0a2948782bc83ee0ea699ef4",
}
AMAZON_ROOT = "8ecde6884f3d87b1125ba31ac3fcb13d7016de7f57cc904fe1cb97c6ae98196e"


def check_bundle(label: str, path: str) -> str:
    context = ssl.create_default_context(cafile=str(path))
    hashes = {hashlib.sha256(cert).hexdigest() for cert in context.get_ca_certs(binary_form=True)}
    if hashes & BAD_ROOTS or AMAZON_ROOT not in hashes:
        raise RuntimeError(label + ": distrusted root present or Amazon Root CA 1 missing")
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certifi", action="store_true", help="also inspect this environment's certifi")
    args = parser.parse_args()
    stores: List[Tuple[str, Optional[str]]] = [("OS", check_bundle("OS", "/etc/ssl/certs/ca-certificates.crt"))]
    if args.certifi:
        import certifi

        stores.append(("certifi", check_bundle("certifi", certifi.where())))
    fixtures = Path(__file__).with_name("certificates")
    certificates = sorted(fixtures.glob("*.pem"))
    if len(certificates) != 9:
        raise RuntimeError("Expected two roots, six intermediates and one positive control")
    # OpenSSL 1.1 (bullseye) has no CAstore; OpenSSL 3 must disable it explicitly.
    help_result = subprocess.run(["openssl", "verify", "-help"], capture_output=True, text=True, check=False)
    isolated = ["-no-CAfile", "-no-CApath"]
    if "-no-CAstore" in help_result.stderr + help_result.stdout:
        isolated.append("-no-CAstore")
    for label, bundle in stores + [("OS directory", None)]:
        location = ["-CAfile", bundle] if bundle else ["-CApath", "/etc/ssl/certs"]
        for certificate in certificates:
            expected = certificate.name == "Amazon_Root_CA_1.pem"
            result = subprocess.run(
                ["openssl", "verify"] + isolated + location + ["-attime", "1792454400", str(certificate)],
                capture_output=True,
                text=True,
                check=False,
            )
            if (result.returncode == 0) != expected:
                raise RuntimeError(label + ": " + certificate.name + ": " + result.stdout + result.stderr)
            if not expected and not re.search(r"error (18|20) at", result.stderr):
                raise RuntimeError("Unexpected rejection reason: " + result.stderr)
        print(label + ": compromised roots/intermediates rejected; Amazon Root CA 1 retained")


if __name__ == "__main__":
    main()
