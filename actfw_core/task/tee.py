import traceback
from queue import Empty, Full, Queue
from typing import Generic, List, TypeVar

from .consumer import _ConsumerMixin
from .producer import _ProducerMixin
from .task import Task

T_OUT = TypeVar("T_OUT")
T_IN = TypeVar("T_IN")


class Tee(Generic[T_OUT, T_IN], Task, _ProducerMixin[T_OUT], _ConsumerMixin[T_IN]):
    """Tee Task."""

    def __init__(self) -> None:
        """"""
        Task.__init__(self)
        _ProducerMixin.__init__(self)
        _ConsumerMixin.__init__(self)

    def _outlet(self, o: T_OUT) -> None:
        while self._is_running():
            for out_queue in self.out_queues:
                try:
                    out_queue.put(o, timeout=1)
                except Full:
                    pass
                except:
                    traceback.print_exc()
            return True
        return False

    def run(self) -> None:
        """Run and start the activity"""
        for i in self._inlet():
            o = i
            self._outlet(o)
            if not self._is_running():
                break
