import base64
import io
import os
import socket
from threading import Lock
from typing import List, Optional

from PIL.Image import Image as PIL_Image

from .task import Isolated


def _read_tokens(conn: socket.socket, n: int) -> List[bytes]:
    result = []
    s = b""
    x = n
    while x > 0:
        c = conn.recv(1)
        if c == b" ":
            x -= 1
            result.append(s)
            s = b""
        else:
            s += c
    return result


def _read_bytes(conn: socket.socket, n: int) -> bytes:
    result = b""
    while len(result) < n:
        result += conn.recv(1024)
    return result


class CommandServer(Isolated):
    sock_path: Optional[str]
    img_lock: Lock
    img: Optional[PIL_Image]

    """Actcast Command Server

    This server handles these commands

    * 'Take Photo'
        * responses cached image as png data

    """

    def __init__(self, sock_path: Optional[str] = None) -> None:
        super(CommandServer, self).__init__()
        self.sock_path = None
        env = "ACTCAST_COMMAND_SOCK"
        if env in os.environ:
            self.sock_path = os.environ[env]
        if sock_path is not None:
            self.sock_path = sock_path
        self.running = True
        self.img_lock = Lock()
        self.img = None

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
            # Wait photo
            while self.running:
                with self.img_lock:
                    if self.img is None:
                        continue
                    else:
                        break
            try:
                assert self.img is not None

                conn, addr = s.accept()
                [request_id, command_id, command_data_length] = map(int, _read_tokens(conn, 3))
                if command_id == 0:  # Take Photo
                    header = "data:image/png;base64,"
                    with self.img_lock:
                        pngimg = io.BytesIO()
                        self.img.save(pngimg, format="PNG")
                        b64img = base64.b64encode(pngimg.getbuffer())
                    conn.sendall(
                        "{} {} {} {}{}\n".format(
                            request_id, 0, len(header) + len(b64img), header, b64img.decode("utf-8")
                        ).encode("utf-8")
                    )
                else:
                    conn.sendall(f"{request_id} 2 0\n".encode())
                conn.close()
            except socket.timeout:
                pass
        os.remove(self.sock_path)

    def update_image(self, image: PIL_Image) -> None:
        """

        Update the cached 'Take Photo' command image.

        Args:
            image (:class:`~PIL.Image`): image

        """
        with self.img_lock:
            self.img = image.copy()
