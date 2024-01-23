from pathlib import Path
from tempfile import TemporaryDirectory

import OpenSSL.crypto
from actfw_core._private.agent_app_protocol.service_server import AgentAppProtocolServiceServer
from actfw_core.service_client import ServiceClient
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

TEST_PRIVATE_KEY_PATH = Path(__file__).parent / "private_key.pem"

SOCKET_NAME = "actcast-service.sock"


def generate_private_key() -> None:
    pkey = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    pem = pkey.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(TEST_PRIVATE_KEY_PATH, "wb") as f:
        f.write(pem)


def load_private_key() -> OpenSSL.crypto.PKey:
    with open(TEST_PRIVATE_KEY_PATH, "rb") as f:
        pem = f.read()
    pkey = serialization.load_pem_private_key(pem, None, default_backend())
    return OpenSSL.crypto.PKey.from_cryptography_key(pkey)


def test_service_server() -> None:
    EXPECTED = (
        "lKnPAcytnInnB27ZRRPSrPeK7HLZJi3pnC9sr-WkoHkdzdbmIOi219AGM2pFnttyoqslgwcWmoxMucA48oHMk5ZshdY4rum2WsAV"
        "Yg7EzjpFgIAKBKCzwqSif4O1_vJ3GtWo3aqn_hO57gzMVq3K_uS7_-_zHFgbKqJ9Ip2v6gsvl1VkDcrOzejB8FIWq6_ldOOky5O9"
        "FaYGCgLFntXTRjx4JCRMLBI7_YEZ9YI94RLrggjBYSKGcRjQ070BhUr5UCivjszwplJhTCIfEehGE3kBiGg2jNul0Gx8fKwOhfh2"
        "bKutBR0ibjuNCDeLIDIGa7MGLPncn7eNfwpZa-LYejlpdeV7pYwl6iOr42za8yPmHvhy1EasR8y1BsbF0FVuX2JNOOFr6OFSsPIc"
        "bjLoOeHbIVqblt1WG2jifik6jTtoAektXPATNXCOxaed2e6MRJKMmfc37g4_4YlMxqmZ0GVB9QHHzgb5U0jyJha54QrEu6gma5eh"
        "5bc8hLarR9sxDiYIy-syAcl6_PawJNYSvmH7aHP6k2jqKFKZCm-7KanA_uN69vAfi1Ir-TW0Fovo6uIbcN0KnRya7DSizvx4vHAu"
        "zZ1A7cs6eVcKyvoE22Kr5WvpjGrgWyoiIKAHHbN4oW5fRfYYU_IHjgFOiVuCjn-eyhxiU5ir6wQQbDHhu_c"
    )

    pkey = load_private_key()

    with TemporaryDirectory() as dir_:
        path = Path(dir_)
        path = path / SOCKET_NAME

        try:
            server = AgentAppProtocolServiceServer(path, pkey)
            server.startup()
            client = ServiceClient(path)
            assert client.rs256(b"hoge") == EXPECTED
        finally:
            server.teardown()
            server.join()


if __name__ == "__main__":
    generate_private_key()
