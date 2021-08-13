import io
import itertools
from typing import Any

from actfw_core.schema.agent_app_protocol import CommandRequest, CommandResponse, ServiceRequest, ServiceResponse


class DummySocket:
    _data: io.BytesIO

    def __init__(self, data: bytes) -> None:
        self._data = io.BytesIO(data)

    def recv(self, size: int) -> bytes:
        return self._data.read(size)

    def is_consumed_all(self) -> bool:
        return self._data.read(1) == b""


def test_roundtrip() -> None:
    def roundtrip(cls: Any, data: bytes) -> None:
        sock = DummySocket(data)
        x, err = cls.parse(sock)
        assert err is None
        assert sock.is_consumed_all()
        assert x.to_bytes() == data

    HUGE_DATA_SIZE = 2 ** 13  # 8KB
    HUGE_DATA = f"0 0 {HUGE_DATA_SIZE} ".encode() + b"a" * HUGE_DATA_SIZE

    CLASSES = [CommandRequest, CommandResponse, ServiceRequest, ServiceResponse]
    DATAS = [b"0 0 0 ", b"0 0 1 a", HUGE_DATA]
    for (cls, data) in itertools.product(CLASSES, DATAS):
        roundtrip(cls, data)
