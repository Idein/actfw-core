import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import ParseResult as urllib_ParseResult
from urllib.parse import urlparse
from uuid import UUID

from .misc import AgentAppProtocolVersion


__all__ = [
    "EnvVar",
]


REQUIRED_MINIMUM_PROTOCOL_VERSION = AgentAppProtocolVersion.parse("1.0.0")


# TODO: check by running application.
@dataclass
class EnvVar:
    """
    Utility class to get environment variables passed from actcast agent.

    For more details of each environment variable, see https://example.com/ .
    """

    # Protocol version of agent-app communication.
    protocol_version: AgentAppProtocolVersion
    # Act ID of the actcast application.  (u64)
    act_id: int
    # Device ID of the device running the actcast application.
    device_id: str
    # ID that identifies the launch of the actcast application, like PID.  (UUIDv4)
    instance_id: UUID
    # Path of socket file to receive command from actcast agent.
    command_sock: Path
    # Path of socket file to send command to actcast agent.
    service_sock: Path
    # URL of SOCKS5 proxy server.
    socks_server: Optional[urllib_ParseResult]

    @classmethod
    def load(cls) -> "EnvVar":
        """
        Load environment variables into dataclass.

        Exceptions:
            Raise :class:`~RuntimeError` if the environment variable not set.
        """

        name = "ACTCAST_PROTOCOL_VERSION"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"environment variable not set: {name}")
        protocol_version = AgentAppProtocolVersion.parse(x)

        if protocol_version < REQUIRED_MINIMUM_PROTOCOL_VERSION:
            raise RuntimeError(f"agent too old, `actfw-core` of this version requires `ACTCAST_PROTOCOL_VERSION >= \"{REQUIRED_MINIMUM_PROTOCOL_VERSION.to_str()}\"`")

        name = "ACTCAST_ACT_ID"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"environment variable not set: {name}")
        actcast_act_id = int(x)

        name = "ACTCAST_DEVICE_ID"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"environment variable not set: {name}")
        actcast_device_id = x

        name = "ACTCAST_INSTANCE_ID"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"environment variable not set: {name}")
        actcast_instance_id = UUID(x)

        name = "ACTCAST_COMMAND_SOCK"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"environment variable not set: {name}")
        actcast_command_sock = Path(x)

        name = "ACTCAST_SERVICE_SOCK"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"environment variable not set: {name}")
        actcast_service_sock = Path(x)

        # Not set if the network manifesto disables network access.
        name = "ACTCAST_SOCKS_SERVER"
        x = os.environ.get(name)
        if x is None:
            actcast_socks_server = None
        else:
            actcast_socks_server = urlparse(f"socks5h://{x}")

        return cls(
            actcast_act_id,
            actcast_device_id,
            actcast_instance_id,
            actcast_command_sock,
            actcast_service_sock,
            actcast_socks_server,
        )
