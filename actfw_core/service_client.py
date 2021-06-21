import base64
import os
import socket
from typing import List

from .command_server import _read_bytes, _read_tokens


class ServiceClient:
    _request_id: int

    """Actcast Service Client

    This client handles these commands

    * 'RS256'
        * sign a message with an actcast device specific secret key.

    """

    def __init__(self) -> None:
        self._request_id = 0

    def _sendrecv(self, command_id: int, payload: str) -> str:
        cmd = f"{self._request_id} {command_id} {len(payload)} {payload}".encode("ascii")
        self._request_id += 1
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        socket_path = os.environ["ACTCAST_SERVICE_SOCK"]
        sock.connect(socket_path)
        sock.sendall(cmd)
        [request_id, command_id, response_length] = map(int, _read_tokens(sock, 3))
        response = _read_bytes(sock, response_length)
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        return response.decode("ascii")

    def rs256(self, payload: bytes) -> str:
        """

        Sign a message with an actcast device specific secret key.

        Args:
            payload (bytes): message

        Returns:
            str: signature (base64url encoded)
        """
        b64encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
        return self._sendrecv(0, b64encoded)


if __name__ == "__main__":
    import json

    agent_service_client = ServiceClient()
    sign = agent_service_client.rs256(
        json.dumps(
            {
                "foo": 1,
                "bar": True,
                "baz": "Test",
            }
        ).encode("ascii")
    )
    print(sign)
    sign = agent_service_client.rs256(b"test")
    print(sign)
