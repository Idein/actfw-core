# type: ignore
# flake8: noqa

from actfw_core._private.app import App
from rustonic.prelude import Unreachable


class ActSetting:
    pass


def main():
    with App.new() as app:
        if app.envvar().actcast_socks_server is None:
            # Programmer cause this situation: the manifesto does not allow network access.
            raise Unreachable("environment variable `ACTCAST_SOCKS_SERVER` not set")

        setting = ActSetting.from_dict(app.setting())

        with app.builder() as b:
            # Capture task
            capture = V4LCameraCapture(
                "/dev/video0", MODEL_INPUT_SIZE, 15, format_selector=V4LCameraCapture.FormatSelector.PROPER
            )
            capture = b.spawn_task(capture)

            # Classifier task
            model = Model()
            classifier = b.spawn_task(Classifier(model, MODEL_INPUT_SIZE))

            presenter = b.spawn_task(Presenter(setting))
            take_photo = b.spawn_task(TakePhotoHandler())
            display = b.spawn_task(Display())

            b.connect(capture, classifier)
            b.connect(classifier, presenter)
            b.connect(presenter, take_photo)
            b.connect(take_photo, display)

            b.build()

        app.run()
