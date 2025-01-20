#!/usr/bin/python3
import threading
import time
from typing import Any

import actfw_core


def test_local_video_server_terminate() -> None:
    # try to catch assert error
    exception = None

    def excepthook(args: Any) -> None:
        nonlocal exception
        exception = args.exc_value

    threading.excepthook = excepthook

    # Actcast application
    app = actfw_core.Application()

    # LocalVideoServer (for mjpeg streaming over http)
    cmd = actfw_core.LocalVideoServer(quality=75)
    app.register_task(cmd)

    # Start application
    th = threading.Thread(target=lambda: app.run())
    th.start()
    # terminate LocalVideoServer task without calling `update_image`
    time.sleep(0.1)
    app.stop()
    th.join()
    assert exception is None
