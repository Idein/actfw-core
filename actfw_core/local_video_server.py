import http.server
import io
import socketserver
import threading
from typing import Any, Optional

from PIL.Image import Image as PIL_Image

from .task import Isolated

PORT = 5100


class ObservableValue:
    def __init__(self) -> None:
        self.value = None
        self.condition = threading.Condition()

    def wait_new_value(self, timeout: Optional[float] = None) -> Optional[PIL_Image]:
        with self.condition:
            self.condition.wait(timeout=timeout)
            return self.value

    def set(self, new_value: Optional[Any]) -> None:
        with self.condition:
            self.value = new_value
            self.condition.notify_all()


class LocalVideoStreamHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, image: ObservableValue, quality: int, *args: Any) -> None:
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
                    if frame is not None:
                        frame.save(
                            jpgimg,
                            format="JPEG",
                            quality=self.quality,
                        )
                    else:
                        continue
                    self.wfile.write(b"--FRAME\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(jpgimg.getvalue())
                    self.wfile.write(b"\r\n")
        except Exception:
            pass


class LocalVideoStreamServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class LocalVideoServer(Isolated):
    def __init__(self, quality: int = 75) -> None:  # 75 is the default value for PIL JPEG quality
        super().__init__()
        self.image = ObservableValue()

        def handler(*args: Any) -> None:
            LocalVideoStreamHandler(self.image, quality, *args)

        self.server = LocalVideoStreamServer(("", PORT), handler)

    def update_image(self, image: PIL_Image) -> None:
        try:
            self.image.set(image)
        except Exception:
            pass

    def run(self) -> None:
        self.server.serve_forever()

    def stop(self) -> None:
        super().stop()
        self.server.shutdown()
        self.server.server_close()
