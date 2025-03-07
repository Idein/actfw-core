# type: ignore
import os
from typing import Tuple

import actfw_core
import libcamera as libcam
import numpy as np
from actfw_core.application import Application
from actfw_core.capture import Frame
from actfw_core.command_server import CommandServer
from actfw_core.libcamera_capture import LibcameraCapture
from actfw_core.task import Consumer, Pipe
from actfw_raspberrypi.vc4 import Display
from PIL import Image

# capture image size
(CAPTURE_WIDTH, CAPTURE_HEIGHT) = (640, 480)

# display area size
(DISPLAY_WIDTH, DISPLAY_HEIGHT) = (640, 480)


class Converter(Pipe):
    def __init__(self, capture_size: Tuple[int, int]) -> None:
        super(Converter, self).__init__()
        self.capture_size = capture_size

    def proc(self, frame: Frame) -> Image.Image:
        rgb_image = Image.frombuffer("RGB", self.capture_size, frame.getvalue(), "raw", "RGB")
        return rgb_image


class Presenter(Consumer):
    def __init__(self, preview_window, cmd: CommandServer) -> None:
        super(Presenter, self).__init__()
        self.preview_window = preview_window
        self.cmd = cmd

    def proc(self, image: Image.Image) -> None:
        # update `Take Photo` image
        self.cmd.update_image(image)
        if self.preview_window is not None:
            self.preview_window.blit(np.asarray(image).tobytes())
            self.preview_window.update()


def run(app: Application, preview_window=None) -> None:
    print("run start...")

    print("initializing tasks...")
    cmd = actfw_core.CommandServer()
    cap = LibcameraCapture((CAPTURE_WIDTH, CAPTURE_HEIGHT), libcam.PixelFormat("BGR888"))

    conv = Converter((CAPTURE_WIDTH, CAPTURE_HEIGHT))
    pres = Presenter(preview_window, cmd)

    print("registering tasks...")
    app.register_task(cmd)
    app.register_task(cap)
    app.register_task(conv)
    app.register_task(pres)

    print("connecting tasks...")
    cap.connect(conv)
    conv.connect(pres)

    print("starting application...")
    app.run()
    print("run end.")


def main() -> None:
    print("main start...")

    print("checking display connection...")
    try:
        with open("/sys/class/drm/card0-HDMI-A-1/status") as f:
            display_connected = f.read().strip() == "connected"
    except FileNotFoundError:
        try:
            with open("/sys/class/drm/card1-HDMI-A-1/status") as f:
                display_connected = f.read().strip() == "connected"
        except FileNotFoundError:
            display_connected = False
    print("checked display connection.")

    # これがないと buster と判定されてしまいディスプレイに表示されなくなる
    # https://github.com/Idein/actfw-raspberrypi/blob/54504f1477b80878d891d7bdbaa852eb14a7a7b2/actfw_raspberrypi/vc4/display.py#L20-L23
    # とりあえず bullseye と判定させておけば動くため raspberrypi-bullseye にしておく
    os.environ["ACTCAST_FIRMWARE_TYPE"] = "raspberrypi-bullseye"

    app = actfw_core.Application()
    if display_connected:
        print("creating display...")
        with Display() as display:
            print(f"created display: {display}")
            preview_area = (0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT)
            capture_size = (CAPTURE_WIDTH, CAPTURE_HEIGHT)
            layer = 16
            print("opening window...")
            with display.open_window(preview_area, capture_size, layer) as preview_window:
                print("run with display")
                run(app, preview_window)
    else:
        print("run without display")
        run(app)
    print("main end.")


if __name__ == "__main__":
    main()
