# import sys
# import time
# from dataclasses import dataclass
# from typing import Tuple

# __all__ = [
#     "States",
# ]


# @dataclass
# class _State:
#     def is_transition_admissible(self, to: "_State") -> bool:
#         return (type(self), type(to)) in _ADMISSIBLE_TRANSITIONS


# @dataclass
# class _Init(_State):
#     def __init__(self) -> None:
#         super().__init__()


# @dataclass
# class _Building(_State):
#     def __init__(self) -> None:
#         super().__init__()


# @dataclass
# class _Startup(_State):
#     def __init__(self) -> None:
#         super().__init__()


# @dataclass
# class _Running(_State):
#     def __init__(self) -> None:
#         super().__init__()


# @dataclass
# class _TemporallyUnavailable(_State):
#     def __init__(self) -> None:
#         super().__init__()


# @dataclass
# class _Terminated(_State):
#     def __init__(self) -> None:
#         super().__init__()


# @dataclass
# class _Restarting(_State):
#     def __init__(self) -> None:
#         super().__init__()


# _ADMISSIBLE_TRANSITIONS: set[Tuple[type(_State), type(_State)]] = set(
#     [
#         # Ordinal transition
#         (_Init, _Building),
#         (_Building, _Startup),
#         (_Startup, _Running),
#         (_Running, _TemporallyUnavailable),
#         (_TemporallyUnavailable, _Running),
#         # Error transition
#         (_Init, _Terminated),
#         (_Init, _Restarting),
#         (_Building, _Terminated),
#         (_Building, _Restarting),
#         (_Startup, _Terminated),
#         (_Startup, _Restarting),
#         (_Running, _Terminated),
#         (_Running, _Restarting),
#         (_TemporallyUnavailable, _Terminated),
#         (_TemporallyUnavailable, _Restarting),
#     ]
# )


# class States:
#     Init = _Init
#     Building = _Building
#     Startup = _Startup
#     Running = _Running
#     TemporallyUnavailable = _TemporallyUnavailable
#     Terminated = _Terminated
#     Restarting = _Restarting


# class _StateManager:
#     _state: _State

#     def __init__(self) -> None:
#         self._state = States.Init()

#     def change_state(self, to: _State) -> None:
#         assert self._state.is_transition_admissible(to)

#         self._state = to

#     def terminated_block_forever(self) -> None:  # -> !
#         assert self._state.is_terminated()

#         DURATION_SECS = 10
#         while True:
#             time.sleep(DURATION_SECS)

#     def restarting_exit(self) -> None:  # -> !
#         assert self._state.is_restarting()

#         sys.exit(1)
