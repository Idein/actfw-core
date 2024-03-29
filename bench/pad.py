import sys

# Add packages
if True:
    sys.path.append(".")
    sys.path.append("..")

import time
from queue import Queue

from actfw_core.util.pad import _PadDiscardingOld

COUNT = 10**6


def f() -> None:
    t_0 = time.time()

    pad_out, pad_in = _PadDiscardingOld().into_pad_pair()  # type: ignore
    c = COUNT
    while c > 0:
        c -= 1
        pad_in.put(None)
        pad_out.get()

    t_1 = time.time()

    t = t_1 - t_0
    fps = COUNT / t
    print(f"t = {t}, fps = {fps}")


def g() -> None:
    t_0 = time.time()

    q: Queue = Queue(1)
    pad_out, pad_in = q, q
    c = COUNT
    while c > 0:
        c -= 1
        pad_in.put(None)
        pad_out.get()

    t_1 = time.time()

    t = t_1 - t_0
    fps = COUNT / t
    print(f"t = {t}, fps = {fps}")


def benchmark() -> None:
    for _ in range(10):
        f()
        # g()


if __name__ == "__main__":
    benchmark()
