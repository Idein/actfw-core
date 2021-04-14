import signal
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


class Printer(Consumer):
    def __init__(self):
        super(Printer, self).__init__()
        self.xs = []

    @property
    def logs(self):
        return self.xs

    def proc(self, x):
        self.xs.append(x)
        # print(x)


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
    printer = Printer()
    app.register_task(printer)

    counter.connect(tee)
    tee.connect(inc0)
    tee.connect(inc1)
    inc0.connect(join)
    inc1.connect(join)
    join.connect(adder)
    adder.connect(printer)

    th = threading.Thread(target=lambda: app.run())
    th.start()
    time.sleep(0.5)
    signal.pthread_kill(threading.get_ident(), signal.SIGINT)
    th.join()

    def expected_log(xs):
        expected = 2
        for actual in xs:
            if expected != actual:
                return False
            expected += 2
        return True

    assert expected_log(printer.logs)
