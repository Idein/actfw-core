import time
from pathlib import Path
from queue import SimpleQueue
from typing import Optional

from .util.thread import LoopThread

DEFAULT_UPDATE_DURATION_SECS = 3
LIVENESS_PROVE_PATH = Path("/tmp/actcast-app-liveness-prove")


class LivenessUpdater:
    _thread: LoopThread
    # _app: App
    _update_duration_secs: int

    # def __init__(self, app: App, update_duration_secs: int):
    def __init__(self, error_ch: SimpleQueue, update_duration_secs: Optional[int]) -> None:
        if update_duration_secs is None:
            update_duration_secs = DEFAULT_UPDATE_DURATION_SECS

        # self._app = app
        self._update_duration_secs = update_duration_secs
        self._thread = LoopThread(error_ch, self._loop_body, daemon=True)

    def startup(self) -> None:
        self._thread.startup()

    # This component will be not teardowned.
    #
    # def teardown(self) -> None:
    #     self._thread.teardown()
    #
    # def join(self) -> None:
    #     self._thread.join()

    def _loop_body(self) -> None:
        LIVENESS_PROVE_PATH.touch()
        time.sleep(self._update_duration_secs)
