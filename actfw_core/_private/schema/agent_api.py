import enum
from actfw_core.compat.dataclasses import dataclass
from typing import List

import socket
from rustonic.std.result import *


def _read_tokens(conn: socket.socket, n: int) -> List[bytes]:
    result = []
    s = b""
    while n > 0:
        c = conn.recv(1)
        if c == b" ":
            n -= 1
            result.append(s)
            s = b""
        else:
            s += c
    return result


def _read_bytes(conn: socket.socket, n: int) -> bytes:
    result = b""
    while len(result) < n:
        result += conn.recv(1024)
    return result


@dataclass(frozen=True, eq=True)
class RequestId:
    _id: int


class CommandKind(enum.Enum):
    TAKE_PHOTO = 0


class Status(enum.Enum):
    OK = 0
    BUSY = 1
    UNIMPLEMENTED = 2
    DEVICE_ERROR = 3
    APP_ERROR = 4
    GENERAL_ERROR = 5


@dataclass(frozen=True, eq=False)
class CommandRequest:
    id_: RequestId
    cmd: CommandKind
    data: str

    @classmethod
    def parse(conn: socket.socket) -> Result["CommandRequest"]:
        try:
            [id_, kind, data_length] = map(int, _read_tokens(conn, 3))
            data = _read_bytes(conn, data_length)
            return Ok(CommandRequest(id_, kind, data))
        except Exception as e:
            return Err(e)


@dataclass(frozen=True, eq=False)
class CommandResponse:
    id_: RequestId
    status: Status
    data: bytes

    @classmethod
    def to_bytes(self) -> bytes:
        id_ = self.id_._id
        kind = self.service.to_int()
        data = self._data
        return f"{id_} {kind} {len(data)} ".encode("utf-8") + data


class ServiceKind(enum.Enum):
    RS_256 = 0


@dataclass(frozen=True, eq=False)
class ServiceRequest:
    id_: RequestId
    service: ServiceKind
    data: bytes

    @classmethod
    def to_bytes(self) -> bytes:
        id_ = self.id_._id
        kind = self.service.to_int()
        data = self._data
        return f"{id_} {kind} {len(data)} ".encode("utf-8") + data


@dataclass(frozen=True, eq=False)
class ServiceResponse:
    id_: RequestId
    service: ServiceKind
    data: bytes

    @classmethod
    def parse(conn: socket.socket) -> Result["ServiceResponse"]:
        try:
            [id_, kind, data_length] = map(int, _read_tokens(conn, 3))
            data = _read_bytes(conn, data_length)
            return Ok(ServiceResponse(id_, kind, data))
        except Exception as e:
            return Err(e)
