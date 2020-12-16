from threading import Thread
from queue import Queue, Empty, Full
import traceback
import inspect
from .task import Task


class Pipe(Task):

    """Straightforward Pipeline Task."""

    def __init__(self):
        """
        """
        super(Pipe, self).__init__()
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
        in_queue_id = 0
        length = len(self.in_queues)
        while self._is_running():
            try:
                i = self.in_queues[in_queue_id].get(timeout=1)
                yield i
                in_queue_id = (in_queue_id + 1) % length
            except Empty:
                pass
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
            o = self.proc(i)
            self._outlet(o)
            if not self._is_running():
                break

    def proc(self, i):
        """
        Pipeline Task Processor

        Args:
            i : task input
        """
        raise NotImplementedError("'proc' must be overridden.")

    def stop(self):
        """Stop the activity"""
        self.running = False

    def connect(self, follow):
        """
        Connect following task.

        Args:
            follow (:class:`~actfw_core.task.Task`): following task
        """
        q = Queue(1)
        follow._add_in_queue(q)
        self._add_out_queue(q)
