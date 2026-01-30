import sys
import threading
from abc import ABC, abstractmethod
from threading import Event, Thread

# TODO: 適切な場所に移動
_act_is_down = Event()

_ACT_DOWN_EXIT_CODE = 99  # TODO: 正式な値に変更する & 定義場所の移動


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
        if threading.current_thread() is threading.main_thread():
            sys.exit(_ACT_DOWN_EXIT_CODE)
        else:
            _act_is_down.set()

    def run(self) -> None:
        """Run and start the activity"""
        raise NotImplementedError()
