import threading
import time

import actfw_core
from actfw_core.task import Consumer, Join, Pipe, Producer, Tee


class Counter(Producer):
    def __init__(self):
        super(Producer, self).__init__()
        self.n = 0

    def proc(self, _):
        time.sleep(0.01)
        n = self.n
        self.n += 1
        return n


class Incrementer(Pipe):
    def __init__(self):
        super(Incrementer, self).__init__()

    def proc(self, x):
        return x + 1


class Adder(Pipe):
    def __init__(self):
        super(Adder, self).__init__()

    def proc(self, xs):
        return sum(xs)


class Logger(Consumer):
    def __init__(self):
        super(Logger, self).__init__()
        self.xs = []

    @property
    def logs(self):
        return self.xs

    def proc(self, x):
        self.xs.append(x)


def test_pipeline():

    app = actfw_core.Application()

    counter = Counter()
    app.register_task(counter)
    tee = Tee()
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
