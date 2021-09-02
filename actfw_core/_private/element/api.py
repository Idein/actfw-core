from dataclasses import dataclass

from ..app import AppSharedData, AppExitReason
from .misc import ElementId, ElementReadiness


@dataclass(frozen=True, eq=False)
class ElementApiContext:
    app_ref: AppSharedData
    elemnet_id: ElementId


class ElementApi:
    _ctx: ElementApiContext

    def __init__(self, ctx: ElementApiContext):
        self._ctx = ctx

    def set_liveness_threshold(self, threshold_secs: int) -> None:
        """
        Set the threshould seconds that the `actfw` framewark regards that the element does not alive.
        TODO: Write document about liveness/readiness.
        """
        assert (type(threshold_secs) is int) and (threshold_secs > 0)

        element_id = self._ctx.element_id
        self._ctx.app_ref.set_element_liveness_threshold(element_id, threshold_secs)

    # def update_readiness(self, readiness: ElementReadiness) -> None:
    #     """
    #     Notify the readiness of the element to the application.

    #     See also [probe of application](TODO).
    #     """
    #     assert type(readiness) is ElementReadiness

    #     element_id = self._ctx.element_id
    #     self._ctx.app_ref.update_element_readiness(element_id, readiness)

    def terminate_app(self, reason: AppExitReason) -> None:
        """
        Terminate entire application.

        Application will send `reason` to actcast server.
        See also [termination process of application](TODO).
        """
        assert type(reason) is AppExitReason

        self._ctx.app_ref.terminate_app(reason)
