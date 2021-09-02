import copy
import time
from typing import Dict, List, Tuple
from queue import Queue

from rustonic.std.sync import Mutex

from ..element.misc import ElementId, ElementLiveness, ElementReadiness
from .exit_reason import AppExitReason


class AppSharedData:
    _update_notice: Queue[None]
    _element_liveness: Mutex[Dict[ElementId, ElementLiveness]]
    _element_readiness: Mutex[Dict[ElementId, ElementReadiness]]
    _exit_reason: Mutex[List[AppExitReason]]

    def __init__(
        self,
        update_notice: Queue[None],
        # error_ch: SimpleQueue[Exception],
        element_ids: List[ElementId],
    ):
        self._update_notice = update_notice
        self._element_liveness = dict((id_, ElementLiveness.new(0)) for id_ in element_ids)
        self._element_readiness = dict((id_, ElementReadiness.initial()) for id_ in element_ids)

    @classmethod
    def new(
        cls,
        element_ids: List[ElementId],
    ) -> Tuple["AppSharedData", Queue[None]]:
        update_notice = Queue(1)
        this = cls(update_notice, element_ids)
        return (this, update_notice)

    def liveness(self) -> bool:
        now = time.time()
        return all([x.liveness(now) for x in self._element_liveness.values()])

    def set_element_liveness_threshold(self, element_id: ElementId, threshold_secs: int) -> None:
        with self._element_liveness.lock() as xs:
            xs[element_id].threshold = threshold_secs

        self._update_notice.put(None)

    def update_element_liveness(self, element_id: ElementId) -> None:
        with self._element_liveness.lock() as xs:
            xs[element_id].update()

        # This does not notify update to `App`.

    # def update_element_readiness(self, element_id: ElementId, readiness: ElementReadiness) -> None:
    #     with self._element_readiness.lock() as xs:
    #         xs[element_id] = readiness

    #     self._update_notice.put(None)

    def terminate_app(self, reason: AppExitReason) -> None:
        with self._exit_reason.lock() as exit_reason:
            if len(exit_reason) == 0:
                exit_reason.put(reason)

        self._update_notice.put(None)
