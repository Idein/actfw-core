import pytest


@pytest.mark.parametrize(
    "from_, import_",
    [
        ("actfw_core", "Application"),
        ("actfw_core", "CommandServer"),
        ("actfw_core", "LocalVideoServer"),
        ("actfw_core.capture", "V4LCameraCapture"),
        ("actfw_core.task", "Consumer, Isolated, Join, Pipe, Producer, Task, Tee"),
    ],
)
def test_import_actfw_core(from_: str, import_: str) -> None:
    exec(f"""from {from_} import {import_}""")
