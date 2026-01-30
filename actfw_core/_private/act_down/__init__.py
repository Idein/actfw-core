import sys
from threading import Event

_act_is_down = Event()

def _exit_as_down():
    _ACT_DOWN_EXIT_CODE = 99
    sys.exit(_ACT_DOWN_EXIT_CODE)
