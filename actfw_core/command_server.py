import base64
import copy
import io
import json
import os
import socket
import sys
from threading import Lock, Thread
from typing import Callable, Optional, TypedDict

from PIL.Image import Image as PIL_Image

from .schema.agent_app_protocol import CommandKind, CommandRequest, CommandResponse, Status
from .task import Isolated


class CustomCommandRequest(TypedDict):
    id: str
    payload: str


class CommandServer(Isolated):
    sock_path: Optional[str]
    img_lock: Lock
    img: Optional[PIL_Image]

    """Actcast Command Server

    This server handles these commands

    * 'Take Photo'
        * responses cached image as png data

    """

    def __init__(
        self, sock_path: Optional[str] = None, custom_command_handler: Optional[Callable[[CustomCommandRequest], str]] = None
    ) -> None:
        super().__init__()
        self.sock_path = None
        env = "ACTCAST_COMMAND_SOCK"
        if env in os.environ:
            self.sock_path = os.environ[env]
        if sock_path is not None:
            self.sock_path = sock_path
        self.running = True
        self.img_lock = Lock()
        self.img = None
        self.custom_command_handler = custom_command_handler

    def run(self) -> None:
        """Run and start the activity"""
        if self.sock_path is None:
            return
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError:
            pass  # ignore
        s.bind(self.sock_path)
        s.settimeout(1)
        s.listen(1)

        while self.running:
            try:
                conn, _ = s.accept()
                Thread(target=self._handle_request, args=(conn,), daemon=True).start()
            except socket.timeout:
                pass
            except Exception as e:
                print(f"Unexpected CommandServer error: {e!r}", file=sys.stderr, flush=True)
                pass
        os.remove(self.sock_path)

    def _handle_request(self, conn: socket.socket) -> None:
        try:
            request = CommandRequest.parse(conn)
        except Exception as e:
            print(f"Failed to parse command request: {e!r}", file=sys.stderr, flush=True)
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            return

        response = None

        if request.kind == CommandKind.TAKE_PHOTO:
            response = self._handle_take_photo(request)
        elif request.kind == CommandKind.CHECK_CUSTOM_COMMAND_AVAILABILITY:
            response = self._handle_custom_command_availability(request)
        elif request.kind == CommandKind.CUSTOM_COMMAND:
            response = self._handle_custom_command(request)

        if response is None:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            return

        conn.sendall(response.to_bytes())
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()

    def _handle_take_photo(self, request: CommandRequest) -> Optional[CommandResponse]:
        # Wait photo
        while self.running:
            with self.img_lock:
                if self.img is None:
                    continue

                header = b"data:image/png;base64,"
                pngimg = io.BytesIO()
                self.img.save(pngimg, format="PNG")
                b64img = base64.b64encode(pngimg.getbuffer())
                data = header + b64img
                return CommandResponse(copy.copy(request.id_), Status.OK, data)

        return None

    def _handle_custom_command_availability(self, request: CommandRequest) -> CommandResponse:
        if self.custom_command_handler is None:
            return CommandResponse(copy.copy(request.id_), Status.UNIMPLEMENTED, b"Custom command handler is not set")
        else:
            return CommandResponse(copy.copy(request.id_), Status.OK, b"")

    def _handle_custom_command(self, request: CommandRequest) -> CommandResponse:
        if self.custom_command_handler is None:
            return CommandResponse(
                copy.copy(request.id_), Status.GENERAL_ERROR, b"Unreachable Error: custom command handler is not set"
            )

        try:
            command_server_request: CustomCommandRequest = json.loads(request.data.decode())
        except Exception as e:
            return CommandResponse(
                copy.copy(request.id_), Status.GENERAL_ERROR, f"Failed to parse custom command payload: {e!r}".encode()
            )

        try:
            payload = self.custom_command_handler(command_server_request)
            return CommandResponse(copy.copy(request.id_), Status.OK, payload.encode())
        except Exception as e:
            return CommandResponse(copy.copy(request.id_), Status.APP_ERROR, f"{e!r}".encode())

    def update_image(self, image: PIL_Image) -> None:
        """

        Update the cached 'Take Photo' command image.

        Args:
            image (:class:`~PIL.Image`): image

        """
        with self.img_lock:
            self.img = image.copy()
