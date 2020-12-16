import os
import signal
import time
import json
from actfw_core.task import Task


class Application:

    """Actcast Application"""

    def __init__(self):
        self.running = True
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)
        self.tasks = []
        self.settings = None
        env = 'ACT_SETTINGS_PATH'
        if env in os.environ:
            try:
                with open(os.environ[env]) as f:
                    self.settings = json.load(f)
            except FileNotFoundError:
                pass

    def _handler(self, sig, frame):
        self.running = False

    def get_settings(self, default_settings):
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

    def register_task(self, task):
        """

        Register the application task.

        Args:
            task (:class:`~actfw_core.task.Task`): task
        """
        if not issubclass(type(task), Task):
            raise TypeError("type(task) must be a subclass of actfw_core.task.Task.")
        self.tasks.append(task)

    def run(self):
        """Start application"""
        for task in self.tasks:
            task.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        except:
            raise

        for task in self.tasks:
            task.stop()
        for task in self.tasks:
            task.join()
