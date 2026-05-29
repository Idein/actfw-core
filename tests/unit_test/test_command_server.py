#!/usr/bin/python3
import base64
import io
import json
import os
import socket
import tempfile
import threading
import time
from typing import Any

import actfw_core
from actfw_core.command_server import CommandServer, CustomCommandRequest
from actfw_core.schema.agent_app_protocol import CommandKind, CommandRequest, CommandResponse, RequestId, Status
from PIL import Image


def _connect_to_command_server(sock_path: str) -> socket.socket:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(sock_path)
            return sock
        except (ConnectionRefusedError, FileNotFoundError):
            sock.close()
            time.sleep(0.01)

    raise TimeoutError(f"CommandServer socket was not ready: {sock_path}")


def _wait_until_socket_is_bound(sock_path: str) -> None:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if os.path.exists(sock_path):
            return
        time.sleep(0.01)

    raise TimeoutError(f"CommandServer socket was not bound: {sock_path}")


def test_take_photo_command_succeeds() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    cmd = CommandServer(sock_path)
    expected_image = Image.new("RGB", (1, 1), (255, 0, 0))
    cmd.update_image(expected_image)
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(CommandRequest(RequestId(1), CommandKind.TAKE_PHOTO, b"").to_bytes())
            response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(1)
        assert response.status == Status.OK
        assert response.data.startswith(b"data:image/png;base64,")

        returned_image = Image.open(io.BytesIO(base64.b64decode(response.data.removeprefix(b"data:image/png;base64,"))))
        assert returned_image.size == expected_image.size
        assert returned_image.mode == expected_image.mode
        assert returned_image.getpixel((0, 0)) == expected_image.getpixel((0, 0))
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_check_custom_command_availability_succeeds() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    cmd = CommandServer(sock_path, custom_command_handler=lambda _request: "")
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(CommandRequest(RequestId(1), CommandKind.CHECK_CUSTOM_COMMAND_AVAILABILITY, b"").to_bytes())
            response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(1)
        assert response.status == Status.OK
        assert response.data == b""
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_check_custom_command_availability_returns_unimplemented_when_handler_is_not_set() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    cmd = CommandServer(sock_path)
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(CommandRequest(RequestId(1), CommandKind.CHECK_CUSTOM_COMMAND_AVAILABILITY, b"").to_bytes())
            response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(1)
        assert response.status == Status.UNIMPLEMENTED
        assert response.data == b"Custom command handler is not set"
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_custom_command_succeeds() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    request_payload = {"id": "command-id", "payload": "custom request"}
    response_payload = "custom response"
    received_request = None

    def custom_command_handler(request: CustomCommandRequest) -> str:
        nonlocal received_request
        received_request = request
        return response_payload

    cmd = CommandServer(sock_path, custom_command_handler=custom_command_handler)
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(
                CommandRequest(RequestId(1), CommandKind.CUSTOM_COMMAND, json.dumps(request_payload).encode()).to_bytes()
            )
            response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(1)
        assert response.status == Status.OK
        assert response.data == response_payload.encode()
        assert received_request == request_payload
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_command_server_accepts_commands_in_parallel() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    blocking_handler_started_event = threading.Event()
    blocking_handler_finished_event = threading.Event()
    blocking_timeout_seconds = 2

    def blocking_custom_command_handler(_payload: CustomCommandRequest) -> str:
        blocking_handler_started_event.set()
        # wait forever
        blocking_handler_finished_event.wait()
        return ""

    cmd = CommandServer(sock_path, custom_command_handler=blocking_custom_command_handler)
    cmd.update_image(Image.new("RGB", (1, 1), (0, 255, 0)))
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as blocking_sock:
            blocking_sock.settimeout(blocking_timeout_seconds)
            blocking_sock.sendall(
                CommandRequest(
                    RequestId(1),
                    CommandKind.CUSTOM_COMMAND,
                    json.dumps({"id": "blocking-command-id", "payload": ""}).encode(),
                ).to_bytes()
            )
            assert blocking_handler_started_event.wait(blocking_timeout_seconds)

            with _connect_to_command_server(sock_path) as sock:
                sock.sendall(CommandRequest(RequestId(2), CommandKind.TAKE_PHOTO, b"").to_bytes())
                response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(2)
        assert response.status == Status.OK
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_custom_command_returns_app_error_when_handler_raises() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"

    def custom_command_handler(request: CustomCommandRequest) -> str:
        raise RuntimeError("custom command failed")

    cmd = CommandServer(sock_path, custom_command_handler=custom_command_handler)
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(
                CommandRequest(
                    RequestId(1),
                    CommandKind.CUSTOM_COMMAND,
                    json.dumps({"id": "command-id", "payload": "custom request"}).encode(),
                ).to_bytes()
            )
            response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(1)
        assert response.status == Status.APP_ERROR
        assert response.data == b"RuntimeError('custom command failed')"
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_command_server_shuts_down_connection_without_response_when_request_is_invalid(capsys: Any) -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    cmd = CommandServer(sock_path)
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.settimeout(1)
            sock.sendall(b"invalid ")

            # Assert (print error message and socket will be shutdown without response and closed)
            assert sock.recv(1) == b""
            captured = capsys.readouterr()
            assert "Failed to parse command request:" in captured.err
            assert "invalid literal for int()" in captured.err
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_socket_timeout_keeps_command_server_running() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    cmd = CommandServer(sock_path)
    cmd.start()

    try:
        _wait_until_socket_is_bound(sock_path)

        # Act
        time.sleep(1.1)

        # Assert
        assert cmd.is_alive()
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_command_server_terminate() -> None:
    # try to catch assert error
    exception = None

    def excepthook(args: Any) -> None:
        nonlocal exception
        exception = args.exc_value

    threading.excepthook = excepthook

    # Actcast application
    app = actfw_core.Application()

    # CommandServer (for `Take Photo` command)
    cmd = actfw_core.CommandServer("/tmp/test.sock")
    app.register_task(cmd)

    # Start application
    th = threading.Thread(target=lambda: app.run())
    th.start()
    # terminate CommandServer task without calling `update_image`
    time.sleep(0.1)
    app.stop()
    th.join()
    assert exception is None
