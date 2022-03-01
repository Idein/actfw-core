from contextlib import AbstractContextManager
from queue import SimpleQueue
from types import TracebackType
from typing import List, Optional, Type, Union

from rustonic.crossbeam.sync import WaitGroup
from rustonic.prelude import unreachable
from rustonic.std.ops.drop import DropContext, ProtocolDrop

from .component.liveness_updator import LivenessUpdater
from .state import AppStates
from .exit_reason import AppExitReason
from ..envvar import EnvVar
from ..state import _StateManager
from ..task import Element
from ..task_state import ElementStates
from ..util.waitgroup_waiter import WaitGroupWaiter
from ..agent_api import AgentAppInterface

__all__ = [
    "App",
    "AppInitGuard",
    "AppGuard",
    "AppBuilderGuard",
    "AppBuilder",
]


class App:
    _state_manager: _StateManager
    _inner: Union["AppInnerInit", "AppInnerBuilding", "AppInnerRunning"]
    _envvar: EnvVar
    _aaif: AgentAppInterface

    def __init__(self, state_manager: _StateManager, envvar: EnvVar, aaif: AgentAppInterface) -> None:
        """
        Private method.  Do not call.  Use `App.new()` insted.
        """
        self._state_manager = state_manager
        self._inner = AppInnerInit()
        self._envvar = envvar
        self._aaif = aaif

    @classmethod
    def new(cls) -> "AppGuard":
        with AppInitGuard() as init_guard:
            envvar = EnvVar.load()
            aaif = AgentAppInterface.startup(envvar)
            app = App(init_guard.into_state_manager(), envvar, aaif)
            return AppGuard(app)

    def builder(self) -> "AppBuilderGuard":
        self._state_manager.change_state(AppStates.Build())
        self._inner = AppInnerBuilding.from_init(self._inner)
        return DropContext(AppBuilder(self._inner))

    def _finish_build(self) -> None:
        self._state_manager.change_state(AppStates.BuildDone())

    def run(self) -> None:
        """
        This method doesn't return successfully.  More precisely,

        - Run the application and block forever if there is no fatal error.
        - Raise exception if a fatal error occured.
        """
        self._state_manager.change_state(AppStates.RunningStartup())
        self._inner = AppInnerRunning.from_building(self._inner, self)
        self._inner.run()


class AppInitGuard(AbstractContextManager["AppInitGuard"]):
    _state_manager: _StateManager  # Arc<Mutex<_StateManager>>

    def __init__(self) -> None:
        self._state_manager = _StateManager

    def __enter__(self) -> "AppInitGuard":
        return self

    def __exit__(
        self,
        exec_type: Optional[Type[BaseException]],
        exec_inst: Optional[BaseException],
        exec_tb: Optional[TracebackType],
    ) -> bool:
        if exec_type is None:
            self._state_manager.change_state(AppStates.Terminated())
            self._state_manager.terminated_block_forever()
        else:
            self._state_manager.change_state(AppStates.Restarting())
            self._state_manager.restarting_exit()

    def into_state_manager(self) -> _StateManager:
        self._state_manager


class AppGuard(AbstractContextManager["App"]):
    _app: App

    def __init__(self, app: App) -> None:
        self._app = app

    def __enter__(self) -> "App":
        return self._app

    def __exit__(
        self,
        exec_type: Optional[Type[BaseException]],
        exec_inst: Optional[BaseException],
        exec_tb: Optional[TracebackType],
    ) -> bool:
        if exec_type is None:
            unreachable("user must call `App.run()`")
        else:
            self._app._state_manager.change_state(AppStates.Restarting())
            self._app._state_manager.restarting_exit()


class AppBuilder(ProtocolDrop):
    _inner: "AppInnerBuilding"  # shared
    _finalized: bool

    def __init__(self, inner: "AppInnerBuilding") -> None:
        self._inner = inner
        self._finalized = False

    # ProtocolDrop
    def drop(self) -> None:
        if not self._finalized:
            raise RuntimeError("user must call `AppBuilder.build()` before `AbstractContextManager.__exit__()`")

        self._app._finish_build()

    def spawn_task(self, task: Element) -> Element:  # (&mut self, Element) -> &mut Element
        return self._inner.spawn_task(task)

    def connect(self, from_: Element, to: Element) -> None:
        from_.connect(to)

    def support_agent_app_command_take_photo(self) -> AgentAppCommandHandlerTakePhoto:
        pass

    def build(self) -> None:
        self._finalized = True


class AppInnerInit:
    pass


class AppInnerBuilding:
    _tasks: List[ElementCell]

    def __init__(self) -> None:
        self._tasks = []

    @classmethod
    def from_init(cls, inner: AppInnerInit) -> "AppInnerRunning":
        return cls()

    # TODO
    def spawn_task(self, task: Element) -> Element:
        cell = ElementCell(task)
        self._tasks.append(cell)
        return task


from .shared_data import AppSharedData
from ..element.cell import ElementCell
from queue import Queue


class AppInnerRunning:
    _app: App
    _tasks: List[ElementCell]

    def __init__(self, app: App, tasks: List[ElementCell]) -> None:
        self._app = app
        (x, q) = AppSharedData.new(
            self._app_shared_data_update_notice,
            [cell.get_id() for cell in tasks],
        )
        self._app_shared_data_update_notice = q
        self._app_shared_data = x
        self._tasks = tasks
        self._error_ch = self._app._error_ch
        # TODO:
        #   app container の liveness == actfw フレームワークの liveness == App の liveness
        # にしてしまった方が良いのでは?
        self._liveness_updater = LivenessUpdater(self._error_ch)

    @classmethod
    def from_building(cls, inner: AppInnerBuilding, app: App) -> "AppInnerRunning":
        return cls(
            app,
            inner._tasks,
        )

    def run(self) -> None:
        self._liveness_updater.startup()

        wg = WaitGroup()

        for task in self._tasks:
            task.change_state(ElementStates.RunningStartup(), wg.clone())

        waiter = WaitGroupWaiter(wg)
        while True:
            self._check_fatal_errors()

            if waiter.is_done():
                break

        for task in self._tasks:
            task.change_state(ElementStates.RunningStartup(), wg.clone())

        waiter = WaitGroupWaiter(wg)
        while True:
            self._check_fatal_errors()

            if waiter.is_done():
                break
