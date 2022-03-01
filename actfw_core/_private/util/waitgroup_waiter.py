from threading import Thread

from rustonic.crossbeam.sync import WaitGroup


class WaitGroupWaiter:
    """
    Auxiliary class to wait `WaitGroup` by busy loop.
    """

    _wg: WaitGroup
    _done: bool  # Note that cpython's bool is atomicbool.
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
