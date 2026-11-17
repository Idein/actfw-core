"""Exercise V4L2 control handling of `Video` without camera hardware."""

import errno
import ctypes
from typing import Dict, List, Optional, Set

import pytest
from actfw_core.v4l2.control import (
    V4L2_CID,
    V4L2_CTRL_FLAG_DISABLED,
    V4L2_CTRL_FLAG_INACTIVE,
    V4L2_CTRL_FLAG_NEXT_CTRL,
    V4L2_CTRL_FLAG_READ_ONLY,
    V4L2_CTRL_FLAG_WRITE_ONLY,
    V4L2_CTRL_TYPE,
    V4L2_EXPOSURE,
)
from actfw_core.v4l2.video import _VIDIOC, ControlReset, Video


class FakeControl:
    def __init__(self, cid: int, name: str, value: int, default: int, type_: int = V4L2_CTRL_TYPE.INTEGER, flags: int = 0):
        self.id = int(cid)
        self.name = name
        self.value = value
        self.default = default
        self.type = int(type_)
        self.flags = flags


class FakeCamera:
    """A UVC camera emulated at the level of VIDIOC_QUERYCTRL / G_CTRL / S_CTRL.

    Like the uvcvideo driver, a control becomes inactive while its automatic mode is enabled
    (`auto_of`: control ID -> (ID of the mode control, values of the mode meaning automatic)).
    """

    def __init__(self, controls: List[FakeControl], auto_of=None, rejected: Optional[Dict[int, Set[int]]] = None):
        self.controls = {c.id: c for c in controls}
        self.auto_of = auto_of or {}
        self.rejected = rejected or {}
        self.writes: List[tuple] = []

    def flags(self, c: FakeControl) -> int:
        flags = c.flags
        if c.id in self.auto_of:
            mode_id, auto_values = self.auto_of[c.id]
            if self.controls[mode_id].value in auto_values:
                flags |= V4L2_CTRL_FLAG_INACTIVE
        return flags

    def ioctl(self, request, arg) -> int:
        obj = arg._obj
        if request == _VIDIOC.QUERYCTRL:
            assert obj.id & V4L2_CTRL_FLAG_NEXT_CTRL
            after = obj.id & ~V4L2_CTRL_FLAG_NEXT_CTRL
            ids = sorted(cid for cid in self.controls if cid > after)
            if not ids:
                return self.fail(errno.EINVAL)
            c = self.controls[ids[0]]
            obj.id = c.id
            obj.type = c.type
            obj.name = (ctypes.c_uint8 * 32)(*c.name.encode())
            obj.default_value = c.default
            obj.flags = self.flags(c)
            return 0
        c = self.controls.get(obj.id)
        if c is None:
            return self.fail(errno.EINVAL)
        if request == _VIDIOC.G_CTRL:
            if self.flags(c) & V4L2_CTRL_FLAG_WRITE_ONLY:
                return self.fail(errno.EACCES)
            obj.value = c.value
            return 0
        if request == _VIDIOC.S_CTRL:
            flags = self.flags(c)
            if flags & (V4L2_CTRL_FLAG_READ_ONLY | V4L2_CTRL_FLAG_INACTIVE | V4L2_CTRL_FLAG_DISABLED):
                return self.fail(errno.EACCES)
            if obj.value in self.rejected.get(c.id, set()):
                return self.fail(errno.EINVAL)
            self.writes.append((c.name, obj.value))
            c.value = obj.value
            return 0
        raise AssertionError(f"unexpected ioctl {request}")

    @staticmethod
    def fail(e: int) -> int:
        ctypes.set_errno(e)
        return -1


def make_video(camera: FakeCamera) -> Video:
    video = Video.__new__(Video)  # skip opening a device
    video._ioctl = camera.ioctl
    return video


def cms_v51bk(exposure_auto: int, exposure_absolute: int, backlight: int) -> FakeCamera:
    """SANWA CMS-V51BK: automatic exposure is only aperture priority (3); AUTO (0) is rejected."""
    return FakeCamera(
        [
            FakeControl(V4L2_CID.BRIGHTNESS, "Brightness", 0, 0),
            FakeControl(V4L2_CID.BACKLIGHT_COMPENSATION, "Backlight Compensation", backlight, 55),
            FakeControl(V4L2_CID.EXPOSURE_AUTO, "Auto Exposure", exposure_auto, 3, V4L2_CTRL_TYPE.MENU),
            FakeControl(V4L2_CID.EXPOSURE_ABSOLUTE, "Exposure Time, Absolute", exposure_absolute, 166),
            FakeControl(V4L2_CID.EXPOSURE_AUTO_PRIORITY, "Exposure, Dynamic Framerate", 1, 0, V4L2_CTRL_TYPE.BOOLEAN),
        ],
        auto_of={V4L2_CID.EXPOSURE_ABSOLUTE: (V4L2_CID.EXPOSURE_AUTO, {0, 3})},
        rejected={V4L2_CID.EXPOSURE_AUTO: {V4L2_EXPOSURE.AUTO, V4L2_EXPOSURE.SHUTTER_PRIORITY}},
    )


def test_set_exposure_time_none_cannot_restore_automatic_exposure() -> None:
    # The problem `reset_controls` solves: AUTO (0) is rejected, so the camera stays in manual exposure.
    camera = cms_v51bk(exposure_auto=V4L2_EXPOSURE.MANUAL, exposure_absolute=10, backlight=55)
    video = make_video(camera)

    assert video.set_exposure_time(None) is False
    assert camera.controls[V4L2_CID.EXPOSURE_AUTO].value == V4L2_EXPOSURE.MANUAL


def test_reset_controls_restores_automatic_exposure() -> None:
    camera = cms_v51bk(exposure_auto=V4L2_EXPOSURE.MANUAL, exposure_absolute=10, backlight=0)
    video = make_video(camera)

    resets = video.reset_controls()

    assert [str(r) for r in resets] == [
        "Backlight Compensation: 0 -> 55",
        "Auto Exposure: 1 -> 3",
        "Exposure, Dynamic Framerate: 1 -> 0",
    ]
    assert all(r.ok for r in resets)
    assert resets[1] == ControlReset(V4L2_CID.EXPOSURE_AUTO, "Auto Exposure", 1, 3, True)
    assert camera.controls[V4L2_CID.EXPOSURE_AUTO].value == V4L2_EXPOSURE.APERTURE_PRIORITY
    # the exposure time is inactive once the exposure mode is automatic: it is not written
    assert ("Exposure Time, Absolute", 166) not in camera.writes
    assert camera.controls[V4L2_CID.EXPOSURE_ABSOLUTE].value == 10


def test_reset_controls_then_manual_exposure() -> None:
    camera = cms_v51bk(exposure_auto=V4L2_EXPOSURE.MANUAL, exposure_absolute=10, backlight=55)
    video = make_video(camera)

    video.reset_controls()
    assert video.set_exposure_time(5) is True

    assert camera.controls[V4L2_CID.EXPOSURE_AUTO].value == V4L2_EXPOSURE.MANUAL
    assert camera.controls[V4L2_CID.EXPOSURE_ABSOLUTE].value == 50


def test_reset_controls_does_nothing_on_defaults() -> None:
    camera = cms_v51bk(exposure_auto=V4L2_EXPOSURE.APERTURE_PRIORITY, exposure_absolute=166, backlight=55)
    camera.controls[V4L2_CID.EXPOSURE_AUTO_PRIORITY].value = 0
    video = make_video(camera)

    assert video.reset_controls() == []
    assert camera.writes == []


def test_reset_controls_skips_unwritable_controls_and_types() -> None:
    camera = FakeCamera(
        [
            FakeControl(V4L2_CID.BRIGHTNESS, "Brightness", 10, 0),
            FakeControl(V4L2_CID.CONTRAST, "Contrast", 10, 0, flags=V4L2_CTRL_FLAG_DISABLED),
            FakeControl(V4L2_CID.SATURATION, "Saturation", 10, 0, flags=V4L2_CTRL_FLAG_READ_ONLY),
            FakeControl(V4L2_CID.HUE, "Hue", 10, 0, flags=V4L2_CTRL_FLAG_WRITE_ONLY),
            FakeControl(V4L2_CID.DO_WHITE_BALANCE, "Do White Balance", 1, 0, V4L2_CTRL_TYPE.BUTTON),
            FakeControl(V4L2_CID.CAMERA_CLASS, "Camera Controls", 1, 0, V4L2_CTRL_TYPE.CTRL_CLASS),
        ]
    )
    video = make_video(camera)

    assert [str(r) for r in video.reset_controls()] == ["Brightness: 10 -> 0"]
    assert camera.writes == [("Brightness", 0)]


def test_reset_controls_reports_failures_and_continues() -> None:
    camera = FakeCamera(
        [
            FakeControl(V4L2_CID.BRIGHTNESS, "Brightness", 10, 0),
            FakeControl(V4L2_CID.GAIN, "Gain", 10, 0),
        ],
        rejected={V4L2_CID.BRIGHTNESS: {0}},
    )
    video = make_video(camera)

    resets = video.reset_controls()

    assert resets == [
        ControlReset(V4L2_CID.BRIGHTNESS, "Brightness", 10, 0, False),
        ControlReset(V4L2_CID.GAIN, "Gain", 10, 0, True),
    ]
    assert str(resets[0]) == "Brightness: 10 -> 0 (failed)"


def test_reset_controls_exclude() -> None:
    camera = FakeCamera(
        [
            FakeControl(V4L2_CID.BRIGHTNESS, "Brightness", 10, 0),
            FakeControl(V4L2_CID.FOCUS_ABSOLUTE, "Focus, Absolute", 476, 210),
        ]
    )
    video = make_video(camera)

    assert [str(r) for r in video.reset_controls(exclude=[V4L2_CID.FOCUS_ABSOLUTE])] == ["Brightness: 10 -> 0"]
    assert camera.controls[V4L2_CID.FOCUS_ABSOLUTE].value == 476


def test_reset_controls_resets_controls_activated_by_a_later_mode() -> None:
    # FOCUS_ABSOLUTE comes before FOCUS_AUTO, and is inactive until autofocus is turned off by the reset.
    camera = FakeCamera(
        [
            FakeControl(V4L2_CID.FOCUS_ABSOLUTE, "Focus, Absolute", 476, 210),
            FakeControl(V4L2_CID.FOCUS_AUTO, "Focus, Automatic Continuous", 1, 0, V4L2_CTRL_TYPE.BOOLEAN),
        ],
        auto_of={V4L2_CID.FOCUS_ABSOLUTE: (V4L2_CID.FOCUS_AUTO, {1})},
    )
    video = make_video(camera)

    resets = video.reset_controls()

    assert [str(r) for r in resets] == ["Focus, Automatic Continuous: 1 -> 0", "Focus, Absolute: 476 -> 210"]
    assert camera.controls[V4L2_CID.FOCUS_ABSOLUTE].value == 210


def test_reset_controls_keeps_the_first_value_of_a_control_reset_twice() -> None:
    # e.g. a gain that the automatic exposure moves back right after the reset
    camera = FakeCamera([FakeControl(V4L2_CID.GAIN, "Gain", 68, 64)])
    original = camera.ioctl

    def ioctl(request, arg):
        result = original(request, arg)
        if request == _VIDIOC.S_CTRL:
            camera.controls[V4L2_CID.GAIN].value = 66
        return result

    video = make_video(camera)
    video._ioctl = ioctl

    assert video.reset_controls() == [ControlReset(V4L2_CID.GAIN, "Gain", 68, 64, True)]


@pytest.mark.parametrize("value", [None, 7])
def test_control_reset_str(value: Optional[int]) -> None:
    assert str(ControlReset(1, "Gain", value, 64, True)) == f"Gain: {value} -> 64"
