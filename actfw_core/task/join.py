import traceback
from queue import Empty, Full, Queue
from threading import Thread
from typing import Generic, List, TypeVar

from ..util.pad import _PadBase, _PadBlocking, _PadIn, _PadOut
from .task import Task

T_OUT = TypeVar("T_OUT")
T_IN = TypeVar("T_IN")


class Join(Task, Generic[T_OUT, T_IN]):
    running: bool
    in_queues: List[_PadOut[T_IN]]
    out_queues: List[_PadIn[T_OUT]]
    out_queue_id: int

    """Join Task."""

    def __init__(self):
        """"""
        super().__init__()
        self.running = True
        self.in_queues = []
        self.out_queues = []
        self.out_queue_id = 0

    def _is_running(self):
        return self.running

    def _add_in_queue(self, q):
        self.in_queues.append(q)

    def _add_out_queue(self, q):
        self.out_queues.append(q)

    def _inlet(self):
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

    def _outlet(self, o):
        length = len(self.out_queues)
        while self._is_running():
            try:
                self.out_queues[self.out_queue_id].put(o, timeout=1)
                self.out_queue_id = (self.out_queue_id + 1) % length
                return True
            except Full:
                pass
            except:
                traceback.print_exc()
        return False

    def run(self):
        """Run and start the activity"""
        for i in self._inlet():
            o = i
            self._outlet(o)
            if not self._is_running():
                break

    def stop(self):
        """Stop the activity"""
        self.running = False

    def connect(self, follow):
        """
        Connect following task.

        Args:
            follow (:class:`~actfw_core.task.Task`): following task
        """
        pad_out, pad_in = self._new_pad().into_pad_pair()
        follow._add_in_queue(pad_out)
        self._add_out_queue(pad_in)

    def _new_pad(self) -> _PadBase[T_OUT]:
        return _PadBlocking()
