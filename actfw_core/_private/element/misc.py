import time
from dataclasses import dataclass

from rustonic.std.sync import Mutex

NEXT_ELEMENT_ID = Mutex([0])


@dataclass(frozen=True, eq=True, hash=True)
class ElementId:
    _id: int

    def new() -> "ElementId":
        with NEXT_ELEMENT_ID.lock() as next_:
            ret = ElementId(next_[0])
            next_[0] += 1
            return ret


DEFAULT_ELEMENT_LIVENESS_DURATION = 10


@dataclass(frozen=False, eq=False)
class ElementLiveness:
    duration_secs: int
    tick: float  # `time.time()`

    @classmethod
    def new(cls, tick: float) -> "ElementLiveness":
        return cls(DEFAULT_ELEMENT_LIVENESS_DURATION, tick)

    def liveness(self, now: float) -> bool:
        return (now - self.tick) < self.duration_secs

    def update(self) -> None:
        self.tick = time.time()


class ElementReadiness:
    pass
