from typing import Generic, Protocol, TypeVar

from .api import ElementApi


T_IN = TypeVar("T_IN")
T_OUT = TypeVar("T_OUT")


# class ProtocolElement(Generic[T_IN, T_OUT], Protocol):
#     """
#     Element of pipeline.  Analogue of `GstElement`.
#     """

#     def new_pad_in(self) -> PadIn[T_OUT]:
#         pass

#     def new_pad_out(self) -> PadOut[T_IN]:
#         pass

#     # def change_state(self, state: ElementStates, api: ElementApi) -> None:
#     #     pass

#     def startup(self, api: ElementApi) -> None:
#         pass

#     def teardown(self, api: ElementApi) -> None:
#         pass

#     def running_loop_body(self, api: ElementApi) -> None:
#         pass


class ProtocolElement(Generic[T_IN, T_OUT], Protocol):
    """
    Element of pipeline.  Analogue of `GstElement`.
    """

    def startup(self, api: ElementApi) -> None:
        pass

    def teardown(self, api: ElementApi) -> None:
        pass

    def running_loop_body(self, api: ElementApi) -> None:
        pass
