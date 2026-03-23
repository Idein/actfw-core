import socket
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, List

import pytest
from actfw_core.schema.agent_app_protocol import ServiceKind, ServiceRequest, ServiceResponse, Status
from actfw_core.service_client import ServiceClient


def create_socket_for_test(
    temp_dir: str,
    response_factory: Callable[[ServiceRequest], ServiceResponse],
) -> tuple[Path, List[ServiceRequest]]:
    socket_path = Path(temp_dir) / "actcast-service.sock"
    requests: List[ServiceRequest] = []
    ready = threading.Event()

    def server() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.bind(str(socket_path))
            sock.listen(1)
            ready.set()
            conn, _ = sock.accept()
            with conn:
                request, _ = ServiceRequest.parse(conn)
                assert request is not None
                requests.append(request)
                response = response_factory(request)
                conn.sendall(response.to_bytes())
                if response.status == Status.OK:
                    # Keep the peer connected until ServiceClient._sendrecv() finishes shutdown().
                    conn.recv(1)

    thread = threading.Thread(target=server)
    thread.start()
    assert ready.wait(timeout=1)
    return socket_path, requests


def test_service_client_stop_act_sends_request_to_agent() -> None:
    # Arrange
    with TemporaryDirectory() as temp_dir:
        socket_path, requests = create_socket_for_test(
            temp_dir,
            lambda request: ServiceResponse(request.id_, Status.OK, b""),
        )
        client = ServiceClient(socket_path)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            client.stop_act()

        # Assert
        assert exc_info.value.code == 0
        assert len(requests) == 1
        assert requests[0].kind == ServiceKind.STOP_ACT
        assert requests[0].data == b""


def test_service_client_stop_act_raises_on_error_status() -> None:
    # Arrange
    with TemporaryDirectory() as temp_dir:
        socket_path, _ = create_socket_for_test(
            temp_dir,
            lambda request: ServiceResponse(request.id_, Status.GENERAL_ERROR, b""),
        )
        client = ServiceClient(socket_path)

        # Act & Assert
        with pytest.raises(RuntimeError):
            client.stop_act()
