import json
import os
import signal
import time
from types import FrameType
from typing import Any, Dict, Iterable, List, Optional

from actfw_core.task import Task


class Application:
    running: bool
    tasks: List[Task]
    settings: Optional[Dict[str, Any]]

    """Actcast Application"""

    def __init__(self, stop_by_signals: Iterable[signal.Signals] = (signal.SIGINT, signal.SIGTERM)) -> None:
        self.running = True
        for sig in stop_by_signals:
            signal.signal(sig, self._handler)
        self.tasks = []
        self.settings = None
        env = "ACT_SETTINGS_PATH"
        if env in os.environ:
            try:
                with open(os.environ[env]) as f:
                    self.settings = json.load(f)
            except FileNotFoundError:
                pass

    def _handler(self, sig: signal.Signals, frame: FrameType) -> None:
        self.stop()

    def get_settings(self, default_settings: Dict[str, Any]) -> Dict[str, Any]:
        """

        Get given Act settings.

        Args:
            default_settings (dict): default settings

        Returns:
            dict: updated settings

        Notes:
            Copy default_settings and overwrite it by given Act settings.

        """
        if not isinstance(default_settings, dict):
            raise TypeError("default_settings must be dict.")
        settings = default_settings.copy()
        if self.settings is not None:
            settings.update(self.settings)
        return settings

    def register_task(self, task: Task) -> None:
        """

        Register the application task.

        Args:
            task (:class:`~actfw_core.task.Task`): task
        """
        if not issubclass(type(task), Task):
            raise TypeError("type(task) must be a subclass of actfw_core.task.Task.")
        self.tasks.append(task)

    def run(self) -> None:
        """Start application"""
        for task in self.tasks:
            task.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        for task in self.tasks:
            task.stop()
        for task in self.tasks:
            task.join()

    def stop(self) -> None:
        """Stop application"""
        self.running = False
