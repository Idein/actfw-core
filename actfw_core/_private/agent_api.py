from typing import Dict, Optional
import socket
import os
from pathlib import Path
from threading import Lock

from .schema.agent_api import RequestId, CommandKind

from rustonic.prelude import Unreachable
from rustonic.std.sync import Mutex
from .schema.agent_api import Command, CommandRequest, CommandResponse, ServiceRequest, ServiceResponse


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
                if not response.id_ in conns:
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


from threading import Thread
from queue import SimpleQueue
import queue

        
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


# @dataclasses(frozen=True, eq=False)
# class AgentAppApiMediator:
#     command_mediator: CommandMediator
#     service_sock: ServiceSock
