from typing import Optional

from .agent_api import CommandMediator, CommandSock, ServiceSock
from .envvar import EnvVar
from .schema.agent_api import CommandKind, CommandRequest, CommandResponse, ServiceRequest, ServiceResponse


class ApiContext:
    _agent_app_api_command_mediator: CommandMediator
    _agent_app_api_service_sock: ServiceSock

    def __init__(self, envvar: EnvVar) -> None:
        command_sock = CommandSock(envvar.actcast_command_sock)
        # TODO: startup
        self._agent_app_api_command_mediator = CommandMediator(command_sock)
        self._agent_app_api_service_sock = ServiceSock(envvar.actcast_service_sock)


class AgentAppCommandApi:
    _ctx: ApiContext

    def __init__(self, ctx: ApiContext) -> None:
        self._ctx = ctx

    def try_recv(self, kind: CommandKind) -> Optional[CommandRequest]:
        return self._ctx._agent_app_api_command_mediator.try_recv(kind)

    def send(self, response: CommandResponse) -> None:
        self._ctx._agent_app_api_command_mediator.send(response)


class AgentAppServiceApi:
    _ctx: ApiContext

    def __init__(self, ctx: ApiContext) -> None:
        self._ctx = ctx

    def send(self, request: ServiceRequest) -> ServiceResponse:
        return self._ctx._agent_app_api_service_sock.send(request)
