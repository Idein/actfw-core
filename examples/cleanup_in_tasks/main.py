import sys
import time

import actfw_core
from actfw_core.task import Consumer, Pipe, Producer


def debug_log(msg, *args, **kwargs):
    kwargs["flush"] = True
    kwargs["file"] = sys.stderr
    print(f"debug_log| {msg}", *args, **kwargs)


class Counter(Producer):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def cleanup(self) -> None:
        # 十分すばやく完了しなければプロセス全体がSIGKILLで終了されうるので注意
        debug_log(f"Counter.cleanup: {self.count}")

    def proc(self) -> int:
        time.sleep(1)
        self.count += 1
        return self.count


class FizzBuzz(Pipe):
    def __init__(self) -> None:
        super().__init__()

    def cleanup(self) -> None:
        # 十分すばやく完了しなければプロセス全体がSIGKILLで終了されうるので注意
        debug_log("FizzBuzz.cleanup")

    def proc(self, count: int) -> str:
        if count % 3 == 0 and count % 5 == 0:
            return "actcast"
        elif count % 3 == 0:
            return "act"
        elif count % 5 == 0:
            return "cast"
        else:
            return f"{count}"


class Logger(Consumer):
    def __init__(self) -> None:
        super().__init__()

    def cleanup(self) -> None:
        # 十分すばやく完了しなければプロセス全体がSIGKILLで終了されうるので注意
        debug_log("Logger.cleanup")

    def proc(self, x: str) -> None:
        actfw_core.heartbeat()
        actfw_core.notify([{"msg": x}])


def main() -> None:
    debug_log("main start")
    app = actfw_core.Application()

    counter = Counter()
    app.register_task(counter)

    fizzbuzz = FizzBuzz()
    app.register_task(fizzbuzz)

    logger = Logger()
    app.register_task(logger)

    counter.connect(fizzbuzz)
    fizzbuzz.connect(logger)

    app.run()
    debug_log("main end")


if __name__ == "__main__":
    main()
