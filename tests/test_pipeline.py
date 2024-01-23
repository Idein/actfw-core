import threading
import time
from typing import List, Tuple

import actfw_core
from actfw_core.task import Consumer, Join, Pipe, Producer, Tee


class Counter(Producer[int]):
    def __init__(self) -> None:
        super().__init__()
        self.n = 0

    def proc(self) -> int:
        time.sleep(0.01)
        n = self.n
        self.n += 1
        return n


class Incrementer(Pipe[int, int]):
    def __init__(self) -> None:
        super().__init__()

    def proc(self, x: int) -> int:
        return x + 1


class Adder(Pipe[int, Tuple[int, ...]]):
    def __init__(self) -> None:
        super().__init__()

    def proc(self, xs: Tuple[int, ...]) -> int:
        return sum(xs)


class ThrouputBottleneck(Pipe[int, int]):
    def __init__(self, duration_secs: float) -> None:
        super().__init__()
        self.duration_secs = duration_secs

    def proc(self, x: int) -> int:
        time.sleep(self.duration_secs)
        return x


class Logger(Consumer[int]):
    xs: List[int]

    def __init__(self) -> None:
        super().__init__()
        self.xs = []

    @property
    def logs(self) -> List[int]:
        return self.xs

    def proc(self, x: int) -> None:
        self.xs.append(x)


def test_pipeline() -> None:
    app = actfw_core.Application()

    counter = Counter()
    app.register_task(counter)
    tee = Tee[int]()
    app.register_task(tee)
    inc0 = Incrementer()
    app.register_task(inc0)
    inc1 = Incrementer()
    app.register_task(inc1)
    join = Join()
    app.register_task(join)
    adder = Adder()
    app.register_task(adder)
    logger = Logger()
    app.register_task(logger)

    counter.connect(tee)
    tee.connect(inc0)
    tee.connect(inc1)
    inc0.connect(join)
    inc1.connect(join)
    join.connect(adder)
    adder.connect(logger)

    th = threading.Thread(target=lambda: app.run())
    th.start()
    time.sleep(0.5)
    app.stop()
    th.join()

    assert len(logger.logs) > 0
    assert all((i + 1) * 2 == x for i, x in enumerate(logger.logs))


# https://github.com/Idein/actfw-core/pull/31#pullrequestreview-656173369
def test_pipeline_slow_but_no_loss() -> None:
    app = actfw_core.Application()

    counter = Counter()
    app.register_task(counter)
    # The value 2 secs comes from the fact that Producer/Pipe classes call `_PadOut.put(timeout=1)`.
    bottleneck = ThrouputBottleneck(2)
    app.register_task(bottleneck)
    logger = Logger()
    app.register_task(logger)

    counter.connect(bottleneck)
    bottleneck.connect(logger)

    th = threading.Thread(target=lambda: app.run())
    th.start()
    time.sleep(10)
    app.stop()
    th.join()

    assert len(logger.logs) > 0
    assert all(i == x for i, x in enumerate(logger.logs))
