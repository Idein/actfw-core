from abc import ABC, abstractmethod
from threading import Thread


class _TaskI(ABC):
    @abstractmethod
    def _is_running(self) -> bool:
        pass


class Task(Thread, _TaskI):
    running: bool

    """Actcast Application Task"""

    def __init__(self):
        """"""
        Thread.__init__(self)

        self.running = True

    def _is_running(self):
        return self.running

    def stop(self):
        """Stop the activity"""
        self.running = False

    def run(self) -> None:
        """Run and start the activity"""
        raise NotImplementedError()
