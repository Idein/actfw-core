import os
import json
from pathlib import Path
import actfw_core.task
import actfw_core.capture
from .application import Application
from .command_server import CommandServer

from actfw_core import _version

__version__ = _version.__version__


def notify(notification, *args, **kwargs):
    """

    Make a notification to Actcast.

    Args:
        notification (list of dict): dicts must be encodable to JSON.

    Example:

        >>> import actfw_core
        >>> actfw_core.notify([{'msg': 'Hello!'}])
        [{"msg": "Hello!"}]

    """
    if type(notification) != list:
        raise TypeError('must be a list of JSON encodable objects.')
    kwargs['flush'] = True
    print(json.dumps(notification), *args, **kwargs)


_default_heartbeat_file = Path('/root/heartbeat')


def _default_heartbeat(*args, **kwargs):
    _default_heartbeat_file.touch()


_heartbeat_function = _default_heartbeat


def set_heartbeat_function(f):
    """

    Set heartbeat action.

    Args:
        f (function): function which execute heartbeat action

    Example:

        >>> import actfw_core
        >>> def heartbeat(): print("working!")
        ...
        >>> actfw_core.set_heartbeat_function(heartbeat)
        >>> actfw_core.heartbeat()
        working!

    """
    global _heartbeat_function
    _heartbeat_function = f


def heartbeat(*args, **kwargs):
    """

    Execute heartbeat action.

    Notes:
        Default action is 'touch /root/heartbeat'.

    """
    _heartbeat_function(*args, **kwargs)
