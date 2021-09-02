from ..util.thread import LoopThread
from .element_state import ElementStates

from rustonic.prelude import Unreachable


from .misc import ElementId
from .api import ElementApi
from .protocol import Element
from .state import ElementStates

from threading import Lock
import queue
from queue import SimpleQueue
import time

from rustonic.prelude import unreachable


from typing import Generic, Protocol, TypeVar


T_IN = TypeVar("T_IN")
T_OUT = TypeVar("T_OUT")


class ElementCell:
    _element: Element[T_IN, T_OUT]
    _element_id: ElementId
    _state: ElementStates
    # _desired_state_lock: Lock
    # _desired_state: ElementStates
    _desired_state_queue: SimpleQueue[ElementStates]
    _thread: LoopThread
    _api: ElementApi

    def __init__(self, element: Element[T_IN, T_OUT]):
        self._element = element
        self._element_id = ElementId.new()
        self._state = ElementStates.INIT
        # self._desired_state_lock = Lock()
        # self._desired_state = ElementStates.INIT
        self._desired_state_queue = SimpleQueue()
        self._thread = LoopThread(self._loop_body)
        # TODO
        self._api = None

    def startup(self) -> None:
        # with self._desired_state_lock:
        #     self._desired_state = ElementStates.RUNNING
        self._desired_state_queue.put(ElementStates.RUNNING)

        self._thread.startup()

    def teardown(self) -> None:
        # with self._desired_state_lock:
        #     self._desired_state = ElementStates.TERMINATED
        self._desired_state_queue.put(ElementStates.TERMINATED)

        self._thread.teardown(allow_extra_loop_for_teardown=True)

    def join(self) -> None:
        self._thread.join()

    def _loop_body(self) -> None:
        # if self._state == ElementStates.INIT:
        #     next_state = ElementStates.STARTING
        #     self._element.change_state(self._state, next_state, self._api)
        #     self._state = next_state
        # elif self._state == ElementStates.STARTING:
        #     next_state = ElementStates.RUNNING
        #     self._element.change_state(self._state, next_state, self._api)
        #     self._state = next_state
        # elif self._state == ElementStates.RUNNING:
        #     self._element.loop_body(self._api)
        # elif self._state == ElementStates.TEMPORARY_ERROR:
        #     next_state = ElementStates.RUNNING
        #     self._element.change_state(self._state, next_state, self._api)
        #     self._state = next_state
        # elif self._state == ElementStates.TERMINATED:
        #     self.teardown()
        # else:
        #     Unreachable()

        # Run reconcillation loop and child's loop body.
        # if self._state != self._desired_state:
        #     change = ElementStateChanges.one_step(self._state, self._desired_state)
        #     res = self._element.change_state(change, self._api)
        #     assert issubclass(res, ElementChangeStateResult)
        #     if res.is_ok():
        #         self._state = change.to()
        #     elif res.is_err():
        #         pass
        #     else:
        #         unreachable()
        # else:
        #     if self._state == ElementStates.RUNNING:
        #         self._element.loop_body(self._api)
        #     else:
        #         time.sleep(1)

        # self._app_ref._notify_element_liveness(self._element_id)
        # self._element.loop_body(self._api)

        # Run reconcillation loop and child's loop body.
        # desired_state: ElementStates
        # with self._desired_state.lock() as desired_state_:
        #     desired_state = desired_state_
        try:
            desired_state = self._desired_state_queue.get_nowait()
        except queue.Empty:
            desired_state = self._state

        if self._state != self._desired_state:
            TRANSITIONS = {
                (ElementStates.INIT, ElementStates.RUNNING): "startup",
                (ElementStates.RUNNING, ElementStates.TERMINATED): "teardown",
                (ElementStates.INIT, ElementStates.TERMINATED): "teardown",
            }

            transition = TRANSITIONS.get((self._state, desired_state))
            if transition == "startup":
                self._element.startup(self._api)
            elif transition == "teardown":
                self._element.teardown(self._api)
            else: # transition is None
                unreachable()

            self._state = desired_state
        else:
            if self._state == ElementStates.RUNNING:
                # TODO
                self._app_ref.update_element_liveness(self._element_id)
                self._element.running_loop_body(self._api)
            else:
                time.sleep(1)
