import traceback
from queue import Empty, Full, Queue
from threading import Thread
from typing import Any, Generator, Generic, List, TypeVar

from ..util.pad import _PadBase, _PadBlocking, _PadIn, _PadOut
from .consumer import _ConsumerMixin
from .producer import _ProducerMixin
from .task import Task


class Join(Task, _ProducerMixin[List[Any]], _ConsumerMixin[Any]):
    """Join Task."""

    def __init__(self) -> None:
        """"""
        Task.__init__(self)
        _ProducerMixin.__init__(self)
        _ConsumerMixin.__init__(self)

    def _inlet(self) -> Generator[List[Any], None, None]:
        while self._is_running():
            try:
                results = []
                for in_queue in self.in_queues:
                    while self._is_running():
                        try:
                            i = in_queue.get(timeout=1)
                            results.append(i)
                            break
                        except Empty:
                            pass
                if len(self.in_queues) == len(results):
                    yield results
                else:
                    assert not self._is_running()
            except GeneratorExit:
                break
            except:
                traceback.print_exc()

    def run(self) -> None:
        """Run and start the activity"""
        for i in self._inlet():
            o = i
            self._outlet(o)
            if not self._is_running():
                break
