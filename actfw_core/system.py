import os
from typing import Optional, cast

class EnvironmentVariableNotSet(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Environment variable {name} is not set. Perhaps the host agent is too old?"

def _get_env_str(name: str) -> str:
    ret = os.environ.get(name)
    if ret is None:
        raise EnvironmentVariableNotSet(name)
    return cast(str, ret)


def _get_env_int(name: str) -> int:
    ret = os.environ.get(name)
    if ret is None:
        raise EnvironmentVariableNotSet(name)
    return int(cast(str, ret))


def get_actcast_protocol_version() -> str:
    "Protocol version of agent-app communication. Since ACTCAST_PROTOCOL_VERSION 1.0.0."
    return _get_env_str("ACTCAST_PROTOCOL_VERSION")


def get_actcast_device_id() -> str:
    "Device ID of the device running the actcast application. Since ACTCAST_PROTOCOL_VERSION 1.0.0."
    return _get_env_str("ACTCAST_DEVICE_ID")


def get_actcast_group_id() -> int:
    "Group ID that the device is belonging to. Since ACTCAST_PROTOCOL_VERSION 1.2.0."
    return _get_env_int("ACTCAST_GROUP_ID")


def get_actcast_act_id() -> int:
    "Act ID of the actcast application. Since ACTCAST_PROTOCOL_VERSION 1.0.0."
    return _get_env_int("ACTCAST_ACT_ID")


def get_actcast_instance_id() -> str:
    "ID that identifies the launch of the actcast application, like PID. Since ACTCAST_PROTOCOL_VERSION 1.0.0."
    return _get_env_str("ACTCAST_INSTANCE_ID")


def get_actcast_device_type() -> str:
    "Device type. Since ACTCAST_PROTOCOL_VERSION 1.1.0."
    return _get_env_str("ACTCAST_DEVICE_TYPE")


def get_act_settings_path() -> str:
    """
    Path of act settings.
    This is rather low level API.
    Use get_settings in Application to get act settings.
    Since ACTCAST_PROTOCOL_VERSION 1.0.0.
    """
    return _get_env_str("ACT_SETTINGS_PATH")


def get_actcast_command_sock() -> str:
    """
    Path of socket file to receive command from actcast agent.
    This is rather low level API.
    Use CommandServer to receive commands from actcast agent.
    Since ACTCAST_PROTOCOL_VERSION 1.0.0.
    """
    return _get_env_str("ACTCAST_COMMAND_SOCK")


def get_actcast_service_sock() -> str:
    """
    Path of socket file to send command to actcast agent.
    This is rather low level API.
    Use ServiceClient to send commands to actcast agent.
    Since ACTCAST_PROTOCOL_VERSION 1.0.0.
    """
    return _get_env_str("ACTCAST_SERVICE_SOCK")


def get_actcast_socks_server() -> Optional[str]:
    "URL of SOCKS5 proxy server. Since ACTCAST_PROTOCOL_VERSION 1.0.0."
    return os.environ.get("ACTCAST_SOCKS_SERVER")


def get_actcast_agent_simulator() -> Optional[str]:
    'Fixed value "actsim" if on actsim environment. Not set otherwise. Since ACTCAST_PROTOCOL_VERSION 1.1.0.'
    return os.environ.get("ACTCAST_AGENT_SIMULATOR")


def get_actcast_firmware_type() -> str:
    "Firmware type of the host. Since ACTCAST_PROTOCOL_VERSION 1.3.0."
    return _get_env_str("ACTCAST_FIRMWARE_TYPE")
