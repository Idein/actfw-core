from typing import Generic, TypeVar

from .consumer import _ConsumerMixin
from .producer import _ProducerMixin
from .task import Task

T_OUT = TypeVar("T_OUT")
T_IN = TypeVar("T_IN")


class Pipe(Generic[T_OUT, T_IN], Task, _ProducerMixin[T_OUT], _ConsumerMixin[T_IN]):
    """Straightforward Pipeline Task."""

    def __init__(self) -> None:
        """"""
        Task.__init__(self)
        _ProducerMixin.__init__(self)
        _ConsumerMixin.__init__(self)

    def cleanup(self) -> None:
        """
        Perform cleanup before exiting.

        This method is executed at the end of `run`, even if an exception is raised.
        Since a long-running cleanup may cause the entire process to be terminated with SIGKILL,
        it must be implemented to complete quickly.
        """
        pass

    def run(self) -> None:
        """Run and start the activity"""
        try:
            for i in self._inlet():
                o = self.proc(i)
                self._outlet(o)
                if not self._is_running():
                    break
        finally:
            self.cleanup()

    def proc(self, i: T_IN) -> T_OUT:
        """
        Pipeline Task Processor
        """
        raise NotImplementedError("'proc' must be overridden.")
