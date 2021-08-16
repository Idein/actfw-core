import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import ParseResult as urllib_ParseResult
from urllib.parse import urlparse
from uuid import UUID

from .util import SimpleSemVer


__all__ = [
    "EnvVar",
]


REQUIRED_MINIMUM_PROTOCOL_VERSION = SimpleSemVer.parse("1.0.0")


@dataclass
class EnvVar:
    """
    Utility class to get environment variables passed from actcast agent.

    For more details of each environment variable, see https://example.com/ .
    """

    # Protocol version of agent-app communication.
    protocol_version: SimpleSemVer
    # Act ID of the actcast application.  (u64)
    act_id: int
    # Device ID of the device running the actcast application.
    device_id: str
    # ID that identifies the launch of the actcast application, like PID.  (UUIDv4)
    instance_id: UUID
    # Path of act settings.
    act_settings_path: Path
    # Path of socket file to receive command from actcast agent.
    command_sock: Path
    # Path of socket file to send command to actcast agent.
    service_sock: Path
    # URL of SOCKS5 proxy server.
    socks_server: Optional[urllib_ParseResult]

    @classmethod
    def from_env(cls) -> "EnvVar":
        """
        Load environment variables into dataclass.

        Exceptions:
            Raise :class:`~RuntimeError` if `ACTCAST_PROTOCOL_VERSION` is smaller than the required version.
        """

        name = "ACTCAST_PROTOCOL_VERSION"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"environment variable not set: {name}")
        protocol_version = SimpleSemVer.parse(x)

        if protocol_version < REQUIRED_MINIMUM_PROTOCOL_VERSION:
            raise RuntimeError(f"agent too old, `actfw-core` of this version requires `ACTCAST_PROTOCOL_VERSION >= \"{REQUIRED_MINIMUM_PROTOCOL_VERSION.to_str()}\"`")

        name = "ACTCAST_ACT_ID"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"unreachable: environment variable not set: {name}")
        act_id = int(x)

        name = "ACTCAST_DEVICE_ID"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"unreachable: environment variable not set: {name}")
        device_id = x

        name = "ACTCAST_INSTANCE_ID"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"unreachable: environment variable not set: {name}")
        instance_id = UUID(x)

        # Note that only this variable have different naming convention from others.
        name = "ACT_SETTINGS_PATH"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"unreachable: environment variable not set: {name}")
        act_settings_path = Path(x)

        name = "ACTCAST_COMMAND_SOCK"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"unreachable: environment variable not set: {name}")
        command_sock = Path(x)

        name = "ACTCAST_SERVICE_SOCK"
        x = os.environ.get(name)
        if x is None:
            raise RuntimeError(f"unreachable: environment variable not set: {name}")
        service_sock = Path(x)

        # Not set if the network manifesto disables network access.
        name = "ACTCAST_SOCKS_SERVER"
        x = os.environ.get(name)
        if x is None:
            socks_server = None
        else:
            socks_server = urlparse(f"socks5h://{x}")

        return cls(
            act_id,
            device_id,
            instance_id,
            act_settings_path,
            command_sock,
            service_sock,
            socks_server,
        )
