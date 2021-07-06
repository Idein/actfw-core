from threading import Thread

from rustonic.crossbeam.sync import WaitGroup

class WaitGroupWaiter:
    _wg: WaitGroup
    _done: bool
    _thread: Thread

    def __init__(self, wg: WaitGroup) -> None:
        self._wg = wg
        self._done = False
        self._thread = Thread(target=self._wait, daemon=True)

        self._thread.start()

    def is_done(self) -> bool:
        if self._done:
            self._thread.join()
            return True
        else:
            return False

    def _wait(self):
        self._wg.wait()
        self._done = True
