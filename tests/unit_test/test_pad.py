from typing import Generic, List, TypeVar

from actfw_core.util.pad import _PadDiscardingOld

T = TypeVar("T")


def listify(pad: _PadDiscardingOld[T]) -> List[T]:
    xs = []
    for _ in range(pad._queue.qsize()):
        xs.append(pad.get())
    return xs


def test_pad_has_the_last_one_element() -> None:
    pad = _PadDiscardingOld()
    pad.put(0)
    pad.put(1)
    assert listify(pad) == [1]

    pad = _PadDiscardingOld()
    pad.put(10)
    pad.put(11)
    pad.put(12)
    assert listify(pad) == [12]
