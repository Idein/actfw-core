import io
import os
import socket
import base64
from threading import Lock
import traceback
from .task import Isolated


def _read_tokens(conn, n):
    result = []
    s = b''
    x = n
    while x > 0:
        c = conn.recv(1)
        if c == b' ':
            x -= 1
            result.append(s)
            s = b''
        else:
            s += c
    return result


def _read_bytes(conn, n):
    result = b''
    while len(result) < n:
        result += conn.recv(1024)
    return result


class CommandServer(Isolated):

    """Actcast Command Server

    This server handles these commands

    * 'Take Photo'
        * responses cached image as png data

    """

    def __init__(self, sock_path=None):
        super(CommandServer, self).__init__()
        self.sock_path = None
        env = 'ACTCAST_COMMAND_SOCK'
        if env in os.environ:
            self.sock_path = os.environ[env]
        if sock_path is not None:
            self.sock_path = sock_path
        self.running = True
        self.img_lock = Lock()
        self.img = None

    def run(self):
        """Run and start the activity"""
        if self.sock_path is None:
            return
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError as e:
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
                conn, addr = s.accept()
                [request_id, command_id, command_data_length] = map(int, _read_tokens(conn, 3))
                command_data = _read_bytes(conn, command_data_length)
                if command_id == 0:  # Take Photo
                    header = "data:image/png;base64,"
                    with self.img_lock:
                        pngimg = io.BytesIO()
                        self.img.save(pngimg, format='PNG')
                        b64img = base64.b64encode(pngimg.getbuffer())
                    conn.sendall("{} {} {} {}{}\n".format(request_id, 0, len(header) +
                                                          len(b64img), header, b64img.decode('utf-8')).encode('utf-8'))
                else:
                    conn.sendall("{} 2 0\n".format(request_id))
                conn.close()
            except socket.timeout:
                pass
            except Exception as e:
                traceback.print_exc()
        os.remove(self.sock_path)

    def update_image(self, image):
        """

        Update the cached 'Take Photo' command image.

        Args:
            image (:class:`~PIL.Image`): image

        """
        with self.img_lock:
            self.img = image.copy()

    def stop(self):
        """Stop the activity"""
        self.running = False
