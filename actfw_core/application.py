import json
import os
import signal
import time

from actfw_core.task import Task


class Application:

    """Actcast Application"""

    def __init__(self, stop_by_signals=[signal.SIGINT, signal.SIGTERM]):
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

    def _handler(self, sig, frame):
        self.stop()

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

    def start(self):
        """Start application"""
        for task in self.tasks:
            task.start()

    @property
    def is_running(self):
        return self.running

    def run(self):
        """Run & Wait application"""
        self.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        except:
            raise
        self.wait()

    def wait(self):
        """Wait application"""
        for task in self.tasks:
            task.stop()
        for task in self.tasks:
            task.join()

    def stop(self):
        """Stop application"""
        self.running = False
