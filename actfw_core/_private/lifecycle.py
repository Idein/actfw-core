from contextlib import AbstractContextManager
from types import TracebackType
from typing import Optional, Type

from .state import _StateManager, States
from .application import ApplicationBuilder


class Lifecycle(AbstractContextManager):
    _state_manager: _StateManager

    def __init__(self) -> None:
        self._state_manager = _StateManager()

    def __enter__(self) -> "Lifecycle":
        return self

    def __exit__(
        self,
        exec_type: Optional[Type[BaseException]],
        exec_inst: Optional[BaseException],
        exec_tb: Optional[TracebackType],
    ) -> bool:
        if exec_type is None:
            self._state_manager.change_state(States.Terminated())
            self._state_manager.terminated_block_forever()
        else:
            self._state_manager.change_state(States.Restarting())
            self._state_manager.restarting_exit()

        def init(self) -> ApplicationBuilder:
            return ApplicationBuilder(self._state_manager)
