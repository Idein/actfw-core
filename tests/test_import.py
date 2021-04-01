from nose2.tools import params


@params(
    {"from": "actfw_core", "import": "Application"},
    {"from": "actfw_core.task", "import": "Producer"},
    {"from": "actfw_core.capture", "import": "V4LCameraCapture"},
    {"from": "actfw_core.task", "import": "Pipe"},
    {"from": "actfw_core.task", "import": "Consumer"},
)
def test_import_actfw_core(param):
    exec(f"""from {param['from']} import {param['import']}""")
