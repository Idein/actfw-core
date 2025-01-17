import http.server
import io
import logging
import socketserver
import threading

from .task import Isolated

PORT = 5100


class ObservableValue:
    def __init__(self):
        self.value = None
        self.condition = threading.Condition()

    def wait_new_value(self, timeout=None):
        with self.condition:
            self.condition.wait(timeout=timeout)
            return self.value

    def set(self, new_value):
        with self.condition:
            self.value = new_value
            self.condition.notify_all()


class LocalVideoCastHandler(http.server.BaseHTTPRequestHandler):

    def __init__(self, image, *args):
        self.image = image
        super().__init__(*args)

    def log_message(*args):
        """Suppress log messages"""
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Age", 0)
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()
        try:
            while True:
                try:
                    frame = self.image.wait_new_value()
                except Exception as e:
                    logging.error(f"Error fetching frame from queue: {e}")
                    continue
                else:
                    jpgimg = io.BytesIO()
                    frame.save(jpgimg, format="JPEG")
                    self.wfile.write(b"--FRAME\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(jpgimg.getvalue())
                    self.wfile.write(b"\r\n")
        except Exception as e:
            logging.error(f"Removed streaming client {self.client_address}: {e}")


class LocalVideoCastServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class LocalVideoCast(Isolated):
    """Local Video Cast Server

    This server handles the streaming of mjpeg to a client over HTTP.
    
    """
    
    def __init__(self):
        super().__init__()
        self.image = ObservableValue()

        def handler(*args):
            LocalVideoCastHandler(self.image, *args)

        self.server = LocalVideoCastServer(("", PORT), handler)

    def update_image(self, image):
        try:
            self.image.set(image)
        except Exception:
            pass

    def run(self):
        self.server.serve_forever()

    def stop(self):
        super().stop()
        self.server.shutdown()
        self.server.server_close()
