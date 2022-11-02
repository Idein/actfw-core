import json
from pathlib import Path

from actfw_core.system import DeviceInfo, DeviceNode, DeviceSupply


def test_device_supply_decode() -> None:
    device_supply_json = """
        {
            "devices": [{"type": "camera",
                         "nodes": [{"path": "/dev/video0", "label": "image_source"}]},
                        {"type": "videocore",
                         "nodes": [{"path": "/dev/vcsm-cma"},
                                   {"path": "/dev/vcio"}]
                        }]
        }
        """

    expected = DeviceSupply(
        devices=[
            DeviceInfo(
                type="camera",
                nodes=[DeviceNode(path=Path("/dev/video0"), label="image_source")],
            ),
            DeviceInfo(
                type="videocore",
                nodes=[
                    DeviceNode(path=Path("/dev/vcsm-cma")),
                    DeviceNode(path=Path("/dev/vcio")),
                ],
            ),
        ]
    )

    assert expected == DeviceSupply.from_json(json.loads(device_supply_json))


def test_device_supply_decode_with_unknown_key() -> None:
    device_supply_json_with_unknown_key = """
        {
            "unknown_key": {"hoge": "hoge"},
            "devices": [{"type": "camera",
                         "nodes": [{"path": "/dev/video0", "label": "image_source"}]},
                        {"type": "videocore",
                         "nodes": [{"path": "/dev/vcsm-cma"},
                                   {"path": "/dev/vcio"}]
                        }]
        }
        """

    expected = DeviceSupply(
        devices=[
            DeviceInfo(
                type="camera",
                nodes=[DeviceNode(path=Path("/dev/video0"), label="image_source")],
            ),
            DeviceInfo(
                type="videocore",
                nodes=[
                    DeviceNode(path=Path("/dev/vcsm-cma")),
                    DeviceNode(path=Path("/dev/vcio")),
                ],
            ),
        ]
    )

    assert expected == DeviceSupply.from_json(json.loads(device_supply_json_with_unknown_key))
