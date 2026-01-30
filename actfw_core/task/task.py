import threading
from abc import ABC, abstractmethod
from threading import Thread

from .._private.act_down import _act_is_down, _exit_as_down

class _TaskI(ABC):
    @abstractmethod
    def _is_running(self) -> bool:
        pass


class Task(Thread, _TaskI):
    running: bool

    """Actcast Application Task"""

    def __init__(self) -> None:
        """"""
        Thread.__init__(self)

        self.running = True

    def _is_running(self) -> bool:
        return self.running and not _act_is_down.is_set()

    def stop(self) -> None:
        """Stop the activity"""
        self.running = False

    def down(self) -> None:
        """Request application shutdown and mark the stop reason.

        If called from the main thread, exit immediately with the Act down exit
        code. If called from a worker thread, set the shared down flag so the
        main loop can exit gracefully.
        """
        if threading.current_thread() is threading.main_thread():
            _exit_as_down()
        else:
            _act_is_down.set()

    def run(self) -> None:
        """Run and start the activity"""
        raise NotImplementedError()
