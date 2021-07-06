import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import ParseResult as urllib_ParseResult
from urllib.parse import urlparse
from uuid import UUID

__all__ = [
    "EnvVar",
]


# TODO: check by running application.
@dataclass
class EnvVar:
    """
    Utility class to get environment variables passed from actcast agent.

    For more details of each environment variable, see https://example.com/ .
    """

    # Act ID of the actcast application.  (u64)
    actcast_act_id: int
    # Device ID of the device running the actcast application.
    actcast_device_id: str
    # ID that identifies the launch of the actcast application, like PID.  (UUIDv4)
    actcast_instance_id: UUID
    # Path of socket file to receive command from actcast agent.
    actcast_command_sock: Path
    # Path of socket file to send command to actcast agent.
    actcast_service_sock: Path
    # URL of SOCKS5 proxy server.
    actcast_socks_server: Optional[urllib_ParseResult]

    @classmethod
    def load(cls) -> "EnvVar":
        """
        Load environment variables into dataclass.

        Exceptions:
            Raise :class:`~RuntimeError` if the environment variable not set.
        """

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
