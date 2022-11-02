import json
from pathlib import Path

import pytest
from actfw_core.system import DeviceInfo, DeviceNode, DeviceSupply, _get_camera_device_info


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


def test_get_camera_device_info_00() -> None:
    devs = DeviceSupply(
        devices=[
            DeviceInfo(
                type="camera",
                nodes=[DeviceNode(path=Path("/dev/video0"), label="image_source")],
            ),
        ]
    )

    expected = DeviceInfo(
        type="camera",
        nodes=[DeviceNode(path=Path("/dev/video0"), label="image_source")],
    )
    assert expected == _get_camera_device_info(devs)


def test_get_camera_device_info_01() -> None:
    devs = DeviceSupply(
        devices=[
            DeviceInfo(
                type="camera",
                nodes=[DeviceNode(path=Path("/dev/video0"))],
            ),
        ]
    )

    expected = DeviceInfo(
        type="camera",
        nodes=[DeviceNode(path=Path("/dev/video0"), label="image_source")],
    )
    assert expected == _get_camera_device_info(devs, "/dev/video0")


def test_get_camera_device_info_02() -> None:
    devs = DeviceSupply(
        devices=[
            DeviceInfo(
                type="camera",
                nodes=[DeviceNode(path=Path("/dev/video0"))],
            ),
        ]
    )

    with pytest.raises(RuntimeError):
        _get_camera_device_info(devs)


def test_get_camera_device_info_03() -> None:
    devs = DeviceSupply(
        devices=[
            DeviceInfo(
                type="camera",
                nodes=[DeviceNode(path=Path("/dev/video0"))],
            ),
        ]
    )

    with pytest.raises(RuntimeError):
        _get_camera_device_info(devs, "/dev/video1")
