import base64
import copy
import os
import socket
import sys
from pathlib import Path
from typing import NoReturn, Optional

from ._private.util.result import ResultTuple
from .schema.agent_app_protocol import RequestId, ServiceKind, ServiceRequest, ServiceResponse, Status

_SERVICE_REQUEST_TIMEOUT_SECONDS = 10.0


class ServiceClient:
    _socket_path: Path
    _request_id: RequestId

    """Actcast Service Client

    This client handles these commands

    * 'RS256'
        * sign a message with an actcast device specific secret key.
    * 'Stop Act'
        * request actcast agent to stop the act.
    * 'Device Shutdown'
        * request actcast agent to shut down the device.

    """

    def __init__(self, socket_path: Optional[Path] = None) -> None:
        if socket_path is None:
            socket_path = Path(os.environ["ACTCAST_SERVICE_SOCK"])

        self._socket_path = socket_path
        self._request_id = RequestId(0)

    def _get_request_id(self) -> RequestId:
        self._request_id = self._request_id.next_()
        return copy.copy(self._request_id)

    def _sendrecv(self, request: ServiceRequest) -> ResultTuple[ServiceResponse, RuntimeError]:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(_SERVICE_REQUEST_TIMEOUT_SECONDS)
        try:
            sock.connect(str(self._socket_path))
            sock.sendall(request.to_bytes())

            response, err = ServiceResponse.parse(sock)
            if isinstance(err, socket.timeout):
                return None, RuntimeError("service request timed out waiting for a response from actcast agent")
            if err:
                return None, RuntimeError("couldn't parse a response from actcast agent: `ServiceResponse.parse()` failed")
            if response is None:
                return None, RuntimeError(f"service request failed: request = {request}, response = {response}")
            if response.status != Status.OK:
                return None, RuntimeError(f"service request failed: request = {request}, response = {response}")

            sock.shutdown(socket.SHUT_RDWR)
            return response, None
        except socket.timeout:
            return None, RuntimeError("service request timed out communicating with actcast agent")
        finally:
            sock.close()

    def rs256(self, payload: bytes) -> str:
        """

        Sign a message with an actcast device specific secret key.

        Args:
            payload (bytes): message

        Returns:
            str: signature (base64url encoded)

        Exceptions:
            RuntimeError
        """
        payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
        request = ServiceRequest(
            self._get_request_id(),
            ServiceKind.RS_256,
            payload,
        )
        response, err = self._sendrecv(request)
        if err:
            raise err
        if response is None:
            raise RuntimeError(f"service request failed: request = {request}, response = {response}")
        return response.data.decode()

    def stop_act(self, reason: Optional[str] = None) -> NoReturn:
        """

        Request actcast agent to stop the act.

        Args:
            reason (Optional[str]): Optional reason for stopping, shown to device operators.
                If omitted, the act stops without a reason (same behavior as before).

        Exceptions:
            RuntimeError
        """
        payload = reason.encode("utf-8") if reason is not None else b""
        request = ServiceRequest(
            self._get_request_id(),
            ServiceKind.STOP_ACT,
            payload,
        )
        response, err = self._sendrecv(request)
        if err:
            raise err
        if response is None:
            raise RuntimeError(f"service request failed: request = {request}, response = {response}")
        sys.exit(0)

    def device_shutdown(self, reason: Optional[str] = None) -> NoReturn:
        """

        Request actcast agent to shut down the device.

        Args:
            reason (Optional[str]): Optional reason for shutting down, shown to device operators.
                If omitted, the device shuts down without a reason.

        Exceptions:
            RuntimeError
        """
        payload = reason.encode("utf-8") if reason is not None else b""
        request = ServiceRequest(
            self._get_request_id(),
            ServiceKind.DEVICE_SHUTDOWN,
            payload,
        )
        response, err = self._sendrecv(request)
        if err:
            raise err
        if response is None:
            raise RuntimeError(f"service request failed: request = {request}, response = {response}")
        sys.exit(0)


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
