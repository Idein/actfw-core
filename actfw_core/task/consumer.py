from queue import Empty
from typing import Generator, Generic, List, Protocol, Tuple, TypeVar, Union

from ..util.pad import _PadOut
from .task import Task, _TaskI

T_IN = TypeVar("T_IN")


class ProtocolConsumer(Generic[T_IN], Protocol):
    def _add_in_queue(self, q: _PadOut[T_IN]) -> None:
        pass

    def _inlet(self) -> Union[Tuple[T_IN, False], Tuple[None, True]]:
        pass


class _ConsumerMixin(Generic[T_IN], _TaskI):
    _in_queues: List[_PadOut[T_IN]]
    _in_queue_index: int

    def __init__(self) -> None:
        self._in_queues = []
        self._in_queue_index = 0

    def _add_in_queue(self, q: _PadOut[T_IN]) -> None:
        self._in_queues.append(q)

    def _inlet(self) -> Union[Tuple[T_IN, False], Tuple[None, True]]:
        index = self._in_queue_index
        self._in_queue_index = (self._in_queue_index + 1) % len(self._in_queues)
        try:
            i = self._in_queues[index].get(timeout=1)
            return i, False
        except Empty:
            return None, True


class Consumer(Generic[T_IN], ProtocolTask, _ConsumerMixin[T_IN]):
    """Consumer Task."""

    def __init__(self) -> None:
        Task.__init__(self)
        _ConsumerMixin.__init__(self)

    # ProtocolElement
    def startup(self, api: TaskApi) -> None:
        self._child.startup(api)

    # ProtocolElement
    def teardown(self, api: TaskApi) -> None:
        self._child.teardown(api)

    # ProtocolElement
    def running_loop_body(self, api: TaskApi) -> None:
        i, timeout = self._inlet()
        if timeout:
            return

        self._child.proc(i)
