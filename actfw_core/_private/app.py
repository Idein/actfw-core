from contextlib import AbstractContextManager
from types import TracebackType
from typing import List, Optional, Type

from rustonic.prelude import Unreachable

from .state import _StateManager
from .task import Task

__all__ = [
    "ApplicationBuilder",
    "App",
]


# class ApplicationLifecycleManager:
#     _state_manager: _StateManager

#     def __init__(self) -> None:
#         self._state_manager = _StateManager()

#     def application_init(self) -> ApplicationLifecycleManagerInit:
#         return ApplicationLifecycleManagerInit(self._state_manager)

#     def with_application(self, app: Application) -> ApplicationLifecycleManagerWithApplication:
#         return ApplicationLifecycleManagerWithApplication(self._state_manager, app)


# class ApplicationLifecycleManagerInit(AbstractContextManager):
#     _state_manager: _StateManager

#     def __init__(self, state_manager: _StateManager) -> None:
#         self._state_manager = state_manager

#     def __enter__(self) -> "Lifecycle":
#         return self

#     def __exit__(
#         self,
#         exec_type: Optional[Type[BaseException]],
#         exec_inst: Optional[BaseException],
#         exec_tb: Optional[TracebackType],
#     ) -> bool:
#         if exec_type is None:
#             self._state_manager.change_state(States.Terminated())
#             self._state_manager.terminated_block_forever()
#         else:
#             self._state_manager.change_state(States.Restarting())
#             self._state_manager.restarting_exit()


class App:
    _state_manager: _StateManager
    _inner: Union[InnerInit, InnerBuilding]
    _envvar: EnvVar

    def __init__(self, state_manager: _StateManager, envvar: EnvVar) -> None:
        """
        Private method.  Do not call.  Use `App.new()` insted.
        """

        self._state_manager = state_manager
        self._inner = InnerInit()
        self._envvar = envvar

    @classmethod
    def new(cls) -> "AppGuard":
        with AppInitGuard() as init_guard:
            envvar = EnvVar.load()
            app = App(init_guard.into_state_manager(), envvar)
            return AppGuard(app)

    def builder(self) -> "AppBuilderGuard":
        self._state_manager.change_state(States.Build())
        builder = AppBuilder(self)
        self._inner = _AppInnerBuild(builder)
        return AppBuilderGuard(builder)

    def _finish_build(self, _builder: AppBuilder) -> None:
        self._state_manager.change_state(States.BuildDone())

    def run(self) -> None:
        """
        This method doesn't return successfully.  More precisely,

        - Run the application and block forever if there is no fatal error.
        - Raise exception if a fatal error occured.
        """
        self._state_manager.change_state(States.RunningStartup())
        builder = self._inner._builder  # Consume `self._inner`.
        api = AppApi(self)
        self._inner = _InnerRunning(api, buider._tasks)
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
            self._state_manager.change_state(States.Terminated())
            self._state_manager.terminated_block_forever()
        else:
            self._state_manager.change_state(States.Restarting())
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
            self._app._state_manager.change_state(States.Terminated())
            self._app._state_manager.terminated_block_forever()
        else:
            self._app._state_manager.change_state(States.Restarting())
            self._app._state_manager.restarting_exit()

        raise Unreachable()


class AppBuilderGuard(AbstractContextManager["AppBuilder"]):
    def __init__(self, builder: "AppBuilder"):
        self._builder = builder

    def __enter__(self) -> "AppBuilder":
        return self._builder

    def __exit__(
        self,
        exec_type: Optional[Type[BaseException]],
        exec_inst: Optional[BaseException],
        exec_tb: Optional[TracebackType],
    ) -> bool:
        if not self._builder._finalized:
            raise RuntimeError("user must call `AppBuilder.build()` before `AppBuilderGuard.__exit__()`")

        self._app._finish_build(self._builder)

        return False


class AppBuilder:
    _finalized: bool
    _tasks: List[Task]

    def __init__(self) -> None:
        self._finalized = False
        self._tasks = []

    def spawn_task(self, task: Task) -> Task:  # (&mut self, Task) -> &mut Task
        self._tasks.append(task)
        return task

    def connect(self, from_: Task, to: Task) -> None:
        from_.connect(to)

    def build(self) -> None:
        self._finalized = True


from queue import SimpleQueue

from rustonic.crossbeam.sync import WaitGroup

from .liveness_updator import LivenessUpdator


class _InnerRunning:
    _app: App
    _tasks: List[TaskCell]

    def __init__(self, app: App, tasks: List[TaskCell]) -> None:
        self._app = app
        self._tasks = tasks
        self._error_ch = SimpleQueue()
        self._liveness_updater = LivenessUpdater(self._error_ch)
        # self._agent_mediator = AgentMediator(app)

    def run(self) -> None:
        wg = WaitGroup()

        for task in self._tasks:
            task.change_state(TaskStates.RunningStartup(), wg.clone())

        waiter = WaitGroupWaiter(wg)
        while True:
            self._check_fatal_errors()

            if waiter.is_done():
                break

        for task in self._tasks:
            task.change_state(TaskStates.RunningStartup(), wg.clone())

        waiter = WaitGroupWaiter(wg)
        while True:
            self._check_fatal_errors()

            if waiter.is_done():
                break


# class ApplicationBuilder:
#     _state_manager: _StateManager
#     _tasks: List[Task]

#     def __init__(self, state_manager: _StateManager) -> None:
#         self._state_manager = state_manager

#     def spawn_task(self, task: Task) -> Task:  # (&mut self, Task) -> &mut Task
#         self._tasks.append(task)
#         return task

#     def build(self) -> "App":  # (self) -> Application
#         return Application(self._state_manager, self._tasks)


# class Application:
#     _state_manager: _StateManager
#     _tasks: List[TaskRunners]

#     def __init__(
#         self,
#         state_manager: _StateManager,
#         tasks: List[Task],
#     ) -> None:
#         self._state_manager = state_manager
#         self._tasks = tasks

#         # task_context = _TaskContext(self)
#         # for task in self._tasks:
#         #     task._set_task_context(task_context)


# class _TaskContext:


#     def __init__(self, app: Application) -> None:
