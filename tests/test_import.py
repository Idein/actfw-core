import pytest


@pytest.mark.parametrize(
    "from_, import_",
    [
        ("actfw_core", "Application"),
        ("actfw_core.capture", "V4LCameraCapture"),
        ("actfw_core.task", "Consumer, Isolated, Join, Pipe, Producer, Task, Tee"),
    ],
)
def test_import_actfw_core(from_, import_):
    exec(f"""from {from_} import {import_}""")
