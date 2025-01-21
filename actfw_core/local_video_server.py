import http.server
import io
import socketserver
import threading
from typing import Any, Generic, Optional, TypeVar

from PIL.Image import Image as PIL_Image

from .task import Isolated

PORT = 5100

T = TypeVar("T")


class _ObservableValue(Generic[T]):
    def __init__(self) -> None:
        self.value: Optional[T] = None
        self.condition = threading.Condition()

    def wait_new_value(self) -> T:
        with self.condition:
            self.condition.wait()
            if self.value is None:
                raise RuntimeError("No value has been set")
            return self.value

    def set(self, new_value: T) -> None:
        with self.condition:
            self.value = new_value
            self.condition.notify_all()


class _LocalVideoStreamHandler(http.server.BaseHTTPRequestHandler):
    def __init__(
        self,
        image: _ObservableValue[PIL_Image],
        quality: int,
        *args: Any,
    ) -> None:
        self.image = image
        self.quality = quality
        super().__init__(*args)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress log messages"""
        pass

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Age", str(0))
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()
        try:
            while True:
                try:
                    frame = self.image.wait_new_value()
                except Exception:
                    continue
                else:
                    jpgimg = io.BytesIO()
                    frame.save(
                        jpgimg,
                        format="JPEG",
                        quality=self.quality,
                    )
                    self.wfile.write(b"--FRAME\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(jpgimg.getvalue())
                    self.wfile.write(b"\r\n")
        except Exception:
            pass


class _LocalVideoStreamServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class LocalVideoServer(Isolated):
    image: _ObservableValue[PIL_Image]
    server: _LocalVideoStreamServer

    """Local Video Server

    This server provides a local video stream on port 5100.

    """

    def __init__(
        self,
        quality: int = 75,  # 75 is the default value of PIL JPEG quality
    ) -> None:
        """

        Initialize a LocalVideoServer instance.

        Args:
            quality (int, optional):
                The image quality setting. Acceptable values range from 0 to 100.

                - 0: Lowest quality
                - 95: Highest quality
                - 100: JPEG lossless (no compression)

                The `quality` parameter corresponds to the `quality` parameter in PIL's `Image.save` method.
                Defaults to `75`.

        """
        super().__init__()
        self.image = _ObservableValue()

        def handler(*args: Any) -> _LocalVideoStreamHandler:
            return _LocalVideoStreamHandler(self.image, quality, *args)

        self.server = _LocalVideoStreamServer(("", PORT), handler)

    def update_image(self, image: PIL_Image) -> None:
        """

        Update the video image.

        Args:
            image (:class:`~PIL.Image`): image

        """

        try:
            self.image.set(image.copy())
        except Exception:
            pass

    def run(self) -> None:
        self.server.serve_forever()

    def stop(self) -> None:
        super().stop()
        self.server.shutdown()
        self.server.server_close()
