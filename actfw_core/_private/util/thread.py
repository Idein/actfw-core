from queue import SimpleQueue
from threading import Thread
from typing import Callable


class LoopThread:
    _error_ch: SimpleQueue
    _loop_body: Callable[[], None]
    _thread: Thread
    _teardown_ch: SimpleQueue

    def __init__(
        self,
        error_ch: SimpleQueue[Exception],
        loop_body: Callable[[], None],
        daemon: bool = False,
    ) -> None:
        self._error_ch = error_ch
        self._loop_body = loop_body
        self._thread = Thread(target=self._loop, daemon=daemon)
        self._teardown_ch = SimpleQueue()

    def _loop(self):
        try:
            while self._teardown_ch.empty():
                self._loop_body()
        except Exception as e:
            self._error_ch.put(e)
