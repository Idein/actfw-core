"""Exercise capture/control flow without requiring libcamera or camera hardware."""

import importlib.util
import math
import sys
import tempfile
from dataclasses import FrozenInstanceError
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def capture_module(monkeypatch):
    class AwbModeEnum(Enum):
        Auto = 0
        Indoor = 4
        Daylight = 5

    controls = SimpleNamespace(AwbModeEnum=AwbModeEnum)
    for name in (
        "AwbEnable",
        "AwbMode",
        "ColourGains",
        "ColourTemperature",
        "Lux",
        "FrameDurationLimits",
        "ScalerCrop",
        "AeEnable",
        "ExposureTime",
        "AnalogueGain",
    ):
        setattr(controls, name, name)
    libcam = MagicMock()
    libcam.controls = controls
    libcam.PixelFormat = str
    libcam.Size = lambda w, h: SimpleNamespace(width=w, height=h)
    monkeypatch.setitem(sys.modules, "libcamera", libcam)
    # Load under a separate name, leaving any real libcamera capture import alone.
    name = "actfw_core._test_libcamera_capture"
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[2] / "actfw_core/libcamera_capture.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "get_actcast_firmware_type", lambda: "raspberrypi-bookworm")
    return module


def make_capture(module, *, awb=None, pixel_format="BGR888", depad=True):
    camera = module.libcam.CameraManager.singleton.return_value.cameras[0]
    camera.configure.return_value = None
    config = camera.generate_configuration.return_value
    config.at.return_value.stride = 64
    kwargs = {} if awb is None else {"awb": awb}
    return module.LibcameraCapture((13, 10), pixel_format, depad=depad, **kwargs)


def image(pixel_format="BGR888", depad=True):
    stride = 39 if depad else 64
    # Unsampled pixels and padding must not contribute to the estimate.
    frame = bytearray([255] * (stride * 10))
    rgb = (30, 100, 160)
    for y in (0, 8):
        for x in (0, 8):
            offset = y * stride + x * 3
            frame[offset : offset + 3] = bytes(rgb if pixel_format == "BGR888" else rgb[::-1])
    return bytes(frame)


def test_defaults_and_validation(capture_module):
    m = capture_module
    assert (m.AwbGreyWorld().gain_r, m.AwbGreyWorld().gain_b, m.AwbGreyWorld().k) == (1.6, 1.6, 0.45)
    cap = make_capture(m)
    assert cap._awb_controls() == {}
    assert cap.awb_status() is None
    for value in (0, -1, math.inf, math.nan):
        with pytest.raises(ValueError):
            m.AwbManual(value, 1)
        with pytest.raises(ValueError):
            m.AwbManual(1, value)
        with pytest.raises(ValueError):
            m.AwbGreyWorld(k=value)
    for value in (0.49, 8.01, math.inf, math.nan):
        with pytest.raises(ValueError):
            m.AwbGreyWorld(gain_r=value)
        with pytest.raises(ValueError):
            m.AwbGreyWorld(gain_b=value)
    with pytest.raises(ValueError):
        m.AwbGreyWorld(k=1.01)
    for value in (None, "greyworld", 4, object()):
        with pytest.raises(TypeError):
            cap.set_awb_settings(value)
    assert cap._awb_controls() == {}


def test_runtime_switches_and_status(capture_module):
    m = capture_module
    cap = make_capture(m, awb=m.AwbManual(1.04, 2.30))
    assert cap._awb_controls() == {"AwbEnable": False, "ColourGains": (1.04, 2.30)}
    cap._update_awb(image(), {"ColourGains": (1.04, 2.30), "ColourTemperature": 4200, "Lux": 200.5})
    snapshot = cap.awb_status()
    assert snapshot == m.AwbStatus(1.04, 2.30, 4200, 200.5)
    with pytest.raises(FrozenInstanceError):
        snapshot.gain_r = 2
    cap.set_awb_settings(m.libcam.controls.AwbModeEnum.Indoor)
    assert cap._awb_controls() == {"AwbEnable": True, "AwbMode": m.libcam.controls.AwbModeEnum.Indoor}
    cap.set_awb_settings(m.Auto.AUTO)
    assert cap._awb_controls() == {"AwbEnable": True, "AwbMode": m.libcam.controls.AwbModeEnum.Auto}
    cap.set_awb_settings(m.AwbGreyWorld(1.2, 2.2, k=0.7))
    assert cap._awb_controls() == {"AwbEnable": False, "ColourGains": (1.2, 2.2)}
    # Switching changes requested controls, not the most recently applied status.
    assert cap.awb_status() is snapshot
    cap._update_awb(image(), {})
    assert cap.awb_status() == m.AwbStatus(None, None, None, None)
    assert snapshot == m.AwbStatus(1.04, 2.30, 4200, 200.5)


@pytest.mark.parametrize("pixel_format", ["BGR888", "RGB888"])
@pytest.mark.parametrize("depad", [True, False])
@pytest.mark.parametrize("k", [0.45, 1.0])
def test_greyworld_pixels_and_applied_gain(capture_module, pixel_format, depad, k):
    m = capture_module
    cap = make_capture(m, awb=m.AwbGreyWorld(1.2, 2.2, k), pixel_format=pixel_format, depad=depad)
    cap._update_awb(image(pixel_format, depad), {"ColourGains": (1.2, 2.2)})
    assert cap._awb_controls()["ColourGains"] == pytest.approx((1.2 * (400 / 121) ** k, 2.2 * (400 / 641) ** k))
    assert cap.awb_status().gain_r == 1.2


def test_greyworld_waits_for_metadata_without_forced_updates(capture_module):
    m = capture_module
    cap = make_capture(m, awb=m.AwbGreyWorld())
    frame = image()
    for metadata in ({}, {"ColourGains": (1.0, 1.0)}, {"ColourGains": (math.nan, 1.6)}):
        cap._update_awb(frame, metadata)
        assert cap._awb_controls()["ColourGains"] == (1.6, 1.6)
    cap._update_awb(frame, {"ColourGains": (1.6, 1.6)})
    target = cap._awb_controls()["ColourGains"]
    assert target != (1.6, 1.6)
    for _ in range(35):
        cap._update_awb(frame, {"ColourGains": (1.6, 1.6)})
        assert cap._awb_controls()["ColourGains"] == target
    # Metadata is float32 on the actual camera; allow small rounding differences.
    applied = tuple(g + 0.00001 for g in target)
    cap._update_awb(frame, {"ColourGains": applied})
    assert cap._awb_controls()["ColourGains"] != target
    cap.set_awb_settings(m.AwbGreyWorld(2, 3, k=1))
    assert cap._awb_controls()["ColourGains"] == (2, 3)
    cap._update_awb(frame, {"ColourGains": target})
    assert cap._awb_controls()["ColourGains"] == (2, 3)


def test_greyworld_clips_and_handles_black(capture_module):
    m = capture_module
    cap = make_capture(m, awb=m.AwbGreyWorld(k=1))
    cap._update_awb(bytes([0, 255, 0] * 130), {"ColourGains": (1.6, 1.6)})
    assert cap._awb_controls()["ColourGains"] == (8, 8)
    cap._update_awb(bytes(390), {"ColourGains": (8, 8)})
    assert cap._awb_controls()["ColourGains"] == (0.5, 0.5)


@pytest.mark.parametrize("mode", ["default", "auto", "indoor", "manual", "greyworld"])
def test_controls_at_camera_start(capture_module, mode, monkeypatch):
    m = capture_module
    options = {
        "default": (None, {}),
        "auto": (None, {"AwbEnable": True, "AwbMode": m.libcam.controls.AwbModeEnum.Auto}),
        "indoor": (m.libcam.controls.AwbModeEnum.Indoor, {"AwbEnable": True, "AwbMode": m.libcam.controls.AwbModeEnum.Indoor}),
        "manual": (m.AwbManual(1.04, 2.30), {"AwbEnable": False, "ColourGains": (1.04, 2.30)}),
        "greyworld": (m.AwbGreyWorld(2, 3, 0.5), {"AwbEnable": False, "ColourGains": (2, 3)}),
    }
    awb, expected = options[mode]
    cap = make_capture(m, awb=awb)
    if mode == "auto":
        cap.set_awb_settings(m.Auto.AUTO)
    cap._camera.start.return_value = None
    m.libcam.FrameBufferAllocator.return_value.allocate.return_value = 0
    monkeypatch.setattr(m.selectors, "DefaultSelector", MagicMock())
    monkeypatch.setattr(cap, "_is_running", lambda: False)
    cap.run()
    cap._camera.start.assert_called_once_with(controls={"FrameDurationLimits": (33333, 33333), **expected})
    cap._camera.stop.assert_called_once()
    cap._camera.release.assert_called_once()


def test_completed_request_metadata_and_requeue(capture_module, monkeypatch):
    m = capture_module
    cap = make_capture(m, awb=m.AwbGreyWorld())
    frame = image()
    with tempfile.TemporaryFile() as file:
        raw_frame = image(depad=False)
        file.write(raw_frame)
        file.flush()
        request = MagicMock()
        request.metadata = {"ColourGains": (1.6, 1.6), "ColourTemperature": 4500, "Lux": 100}
        request.buffers = {
            "stream": SimpleNamespace(planes=[SimpleNamespace(fd=file.fileno(), length=len(raw_frame), offset=0)])
        }
        cap._cm.get_ready_requests.return_value = [request]
        cap._camera.queue_request.return_value = None
        calls = []

        def outlet(output):
            assert output.getvalue() == frame
            assert cap.awb_status() == m.AwbStatus(1.6, 1.6, 4500, 100)
            # A concurrent application switch must win over the previous GW update.
            cap.set_awb_settings(m.AwbManual(1.04, 2.30))
            calls.append("outlet")

        monkeypatch.setattr(cap, "_outlet", outlet)
        request.reuse.side_effect = lambda: calls.append("reuse")
        request.set_control.side_effect = lambda key, value: calls.append((key, value))
        cap._camera.queue_request.side_effect = lambda req: calls.append("queue")
        cap._handle_camera_event()
        assert calls == ["outlet", "reuse", ("AwbEnable", False), ("ColourGains", (1.04, 2.30)), "queue"]

        cap._camera.queue_request.side_effect = None
        cap._camera.queue_request.return_value = -5
        with pytest.raises(m.QueueRequestError):
            cap._handle_camera_event()
