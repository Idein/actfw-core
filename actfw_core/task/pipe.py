from typing import Generic, Protocol, Tuple, TypeVar, Union

from .consumer import _ConsumerMixin
from .producer import _ProducerMixin
from .task import Task

T_OUT = TypeVar("T_OUT")
T_IN = TypeVar("T_IN")


class ProtocolPipe(Generic[T_IN, T_OUT], Protocol):
    def proc(self, i: T_IN) -> Union[Tuple[T_OUT, False], Tuple[None, True]]:
        """
        Process an input T_IN and generate an output T_OUT.
        
        If success, return Tuple[T_OUT, False].
        If timeouted, return Tuple[T_OUT, True].
        If got an error, raise the error.  Raising error stop the task.
        """
        pass


class Pipe(Generic[T_IN, T_OUT], ProtocolTask, _ProducerMixin[T_OUT], _ConsumerMixin[T_IN]):
    """Straightforward Pipeline Task."""

    _child: ProtocolPipe[T_IN, T_OUT]

    def __init__(self, child: ProtocolPipe[T_IN, T_OUT]) -> None:
        """"""
        Task.__init__(self)
        _ProducerMixin.__init__(self)
        _ConsumerMixin.__init__(self)

        self._child = child

    # ProtocolTask
    def loop_body(self) -> None:
        i, timeout = self._inlet()
        if timeout:
            return

        o, timeout = self._child.proc(i)
        if timeout:
            return

        self._outlet(o)
