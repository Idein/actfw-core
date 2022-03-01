import queue
import socket
from pathlib import Path
from queue import SimpleQueue
from threading import Lock, Thread
from typing import Dict, Optional
from dataclasses import dataclass

from rustonic.prelude import Unreachable
from rustonic.std.sync import Mutex

from .schema.agent_api import CommandKind, CommandRequest, CommandResponse, RequestId, ServiceRequest, ServiceResponse
from .envvar import EnvVar


class CommandSock:
    """
    This class is sharable and thread safe.
    """

    # _path: Path
    _sock: socket.socket
    _recv_lock: Lock
    _send_lock: Lock
    _conns: Mutex[Dict[RequestId, socket.socket]]

    def __init__(self, path: Path) -> None:
        # self._path = Path
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._recv_lock = Lock()
        self._send_lock = Lock()
        self._conns = Mutex({})

        # os.unlink(self._path)
        self._sock.bind(self._path)
        self._sock.settimeout(1)
        self._sock.listen(1)

    def recv(self) -> CommandRequest:
        with self._recv_lock:
            (conn, addr) = self._sock.accept()
            request = CommandRequest.parse(conn)
            with self._conns.lock() as conns:
                conns[request.id_] = conn
            return request

    def send(self, response: CommandResponse) -> None:
        # I guess `self._send_lock` can be omited.
        with self._send_lock:
            with self._conns.lock() as conns:
                if response.id_ not in conns:
                    raise Unreachable(f"misuse of `CommandSock.send(), response id invalid: respanse = {response}`")

                conn = conns[response.id_]
                del conns[response.id_]

            conn.sendall(response.to_bytes())
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()


class ServiceSock:
    _path: Path

    def __init__(self, path: Path) -> None:
        self._path = path

    def send_recv(self, request: ServiceRequest) -> ServiceResponse:
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.connect(self._path)
        conn.sendall(request.to_bytes())
        response = ServiceResponse.parse(conn)
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()
        return response


class CommandMediator:
    _sock: CommandSock
    _recv_thread: Thread
    _teardown_ch: SimpleQueue[None]
    _request_queue: "CommandRequestQueue"

    def __init__(self, sock: CommandSock) -> None:
        self._recv_thread = Thread(target=self._run)
        self._sock = sock
        self._teardown_ch = SimpleQueue()

    def startup(self) -> None:
        self._recv_thread.start()

    def teardown(self) -> None:
        self._teardown_ch.put(None)

    def join(self) -> None:
        self._recv_thread.join()

    def _run(self) -> None:
        while self._teardown_ch.empty():
            request = self._sock.recv()
            self._request_queue.push(request)

    def try_recv(self, kind: CommandKind) -> Optional[CommandRequest]:
        return self._request_queue.pop(kind)

    def send(self, response: CommandResponse) -> None:
        self._sock.send(response)


class CommandRequestQueue:
    _queues: Dict[CommandKind, SimpleQueue[CommandRequest]]

    def __init__(self):
        # fmt: off
        self._queues = dict((kind, SimpleQueue())
                            for kind in CommandKind)

    def push(self, request: CommandRequest) -> None:
        self._queues[request.cmd].put(request)

    def pop(self, kind: CommandKind) -> Optional[CommandRequest]:
        try:
            return self._queues[kind].get_nowait()
        except queue.Empty:
            return None


# @dataclass(frozen=True, eq=False)
# class AgentAppInterface:
#     command_mediator: CommandMediator
#     service_sock: ServiceSock

#     @classmethod
#     def startup(cls, envvar: EnvVar) -> "AgentAppInterface":
#         command_sock = CommandSock(envvar.command_sock)
#         command_mediator = CommandMediator(command_sock)
#         command_mediator.startup()
#         service_sock = ServiceSock(envvar.service_sock)
#         return cls(command_mediator, service_sock)


# def ProtocolAgentAppCommandHandler(Protocol):
#     def _push_request(self, request: CommandRequest) -> None:
#         pass


# class AgentAppCommandHandlerTakePhoto(ProtocolAgentAppCommandHandler):
#     _queue: SimpleQueue[CommandRequest]

#     def __init__(self) -> None:
#         self._queue = SimpleQueue()

#     # ProtocolAgentAppCommandHandler
#     def _push_request(self, request: CommandRequest) -> None:
#         assert request.cmd == CommandKind.TAKE_PHOTO
#         self._queue.push(request)

#     def try_recv(self) -> Optional[CommandRequest]:
#         return self._queue.get_nowait()

#     def send(self, response: CommandResponse) -> None:
#         self._sock.send(response)
