#!/usr/bin/python3
import base64
import io
import os
import socket
import tempfile
import threading
import time
from typing import Any

import actfw_core
from actfw_core.command_server import CommandServer
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
        assert response.status == Status.OK
        assert response.data == b""
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_custom_command_succeeds() -> None:
    # Arrange
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    received_data = None

    def custom_command_handler(data: bytes) -> bytes:
        nonlocal received_data
        received_data = data
        return b"custom response"

    cmd = CommandServer(sock_path, custom_command_handler=custom_command_handler)
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(CommandRequest(RequestId(1), CommandKind.CUSTOM_COMMAND, b"custom request").to_bytes())
            response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(1)
        assert response.status == Status.OK
        assert response.data == b"custom response"
        assert received_data == b"custom request"
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

    def blocking_custom_command_handler(_payload: bytes) -> bytes:
        blocking_handler_started_event.set()
        # wait forever
        blocking_handler_finished_event.wait()
        return b""

    cmd = CommandServer(sock_path, custom_command_handler=blocking_custom_command_handler)
    cmd.update_image(Image.new("RGB", (1, 1), (0, 255, 0)))
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as blocking_sock:
            blocking_sock.settimeout(blocking_timeout_seconds)
            blocking_sock.sendall(CommandRequest(RequestId(1), CommandKind.CUSTOM_COMMAND, b"").to_bytes())
            blocking_handler_started_event.wait(blocking_timeout_seconds)

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
    received_data = None

    def custom_command_handler(data: bytes) -> bytes:
        nonlocal received_data
        received_data = data
        raise RuntimeError("custom command failed")

    cmd = CommandServer(sock_path, custom_command_handler=custom_command_handler)
    cmd.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(CommandRequest(RequestId(1), CommandKind.CUSTOM_COMMAND, b"custom request").to_bytes())
            response, err = CommandResponse.parse(sock)

        # Assert
        assert err is None
        assert response is not None
        assert response.id_ == RequestId(1)
        assert response.status == Status.APP_ERROR
        assert response.data == b""
        assert received_data == b"custom request"
    finally:
        cmd.stop()
        cmd.join()
        tmpdir.cleanup()


def test_parse_error_raises_runtime_error() -> None:
    # Arrange
    exception = None
    tmpdir = tempfile.TemporaryDirectory(prefix="actfw-", dir="/tmp")
    sock_path = f"{tmpdir.name}/command.sock"
    cmd = CommandServer(sock_path)

    def run_command_server() -> None:
        nonlocal exception
        try:
            cmd.run()
        except RuntimeError as e:
            exception = e

    thread = threading.Thread(target=run_command_server)
    thread.start()

    try:
        # Act
        with _connect_to_command_server(sock_path) as sock:
            sock.sendall(b"invalid ")

        thread.join(2)

        # Assert
        assert isinstance(exception, RuntimeError)
        assert str(exception) == "couldn't parse a request from actcast agent: `CommandRequest.parse()` failed"
    finally:
        cmd.stop()
        thread.join()
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
