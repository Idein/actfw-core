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
            capture_ = V4LCameraCapture(
                "/dev/video0", MODEL_INPUT_SIZE, 15, format_selector=V4LCameraCapture.FormatSelector.PROPER
            )
            capture = b.spawn_task(capture_)

            # Classifier task
            model = Model()
            classifier = b.spawn_task(Classifier(model, MODEL_INPUT_SIZE))

            presenter = b.spawn_task(Presenter(setting))

            take_photo_ = TakePhotoHandler(b.support_agent_app_command_take_photo())
            take_photo = b.spawn_task(take_photo_)
            
            display = b.spawn_task(Display())

            b.connect(capture, classifier)
            b.connect(classifier, presenter)
            b.connect(presenter, take_photo)
            b.connect(take_photo, display)

            b.build()

        app.run()



# class SimpleElementBase(ProtocolElement):
#     def __init__(self) -> None:
#         self._helper = SimpleElementBaseHelper()

#     def new_pad_in(self) -> PadIn[T_OUT]:
        

from typing import Gereric, TypeVar


T_IN = TypeVar("T_IN")
T_OUT = TypeVar("T_OUT")


class TakePhotoHandler(ProtocolPipe[T_IN, T_OUT]):
    _handler: AgentAppCommandHandlerTakePhoto

    def __init__(self, handler: AgentAppCommandHandlerTakePhoto) -> None:
        super().__init__()

        self._handler = handler

    def proc(self, api: ElementApi, x: T_IN) -> T_OUT:
                
