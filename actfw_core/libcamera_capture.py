"""
LibcameraCapture module.

Note:
    This module is only available in ActcastOS4 or later.
"""

from collections import deque
from dataclasses import dataclass
import math
import mmap
import selectors
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

import libcamera as libcam
from actfw_core.capture import Frame
from actfw_core.system import EnvironmentVariableNotSet, get_actcast_firmware_type
from actfw_core.task import Producer
from actfw_core.unicam_isp_capture import Auto
from actfw_core.util.pad import _PadBase, _PadDiscardingOld


def _validate_awb_gain(gain: float) -> None:
    if not math.isfinite(gain) or gain <= 0:
        raise ValueError("AWB gains must be finite and greater than zero")


@dataclass(frozen=True)
class AwbManual:
    """Disable libcamera AWB and apply fixed red and blue gains.

    Gains must be positive and finite, and within the camera's supported range.
    """

    gain_r: float
    gain_b: float

    def __post_init__(self) -> None:
        _validate_awb_gain(self.gain_r)
        _validate_awb_gain(self.gain_b)


@dataclass(frozen=True)
class AwbGreyWorld:
    """Estimate white balance from the output image, sampled every eight pixels.

    ``gain_r`` and ``gain_b`` are the initial gains. ``k`` damps the multiplicative
    correction: ``next_gain = applied_gain * (sum_g / (sum_channel + 1)) ** k``.
    It must be in (0, 1]; smaller values make the adjustment more gradual.
    Updated gains are limited to [0.5, 8.0]. Initial gains must also be in this range.

    Updates wait until metadata confirms that the preceding gains were applied.
    As with other grey-world algorithms, scenes dominated by a single colour can
    produce a colour cast; convergence depends on the scene and camera processing.
    """

    gain_r: float = 1.6
    gain_b: float = 1.6
    k: float = 0.45

    def __post_init__(self) -> None:
        for gain in (self.gain_r, self.gain_b):
            _validate_awb_gain(gain)
            if not 0.5 <= gain <= 8.0:
                raise ValueError("Grey-world initial gains must be in [0.5, 8.0]")
        if not math.isfinite(self.k) or not 0 < self.k <= 1:
            raise ValueError("Grey-world k must be finite and in (0, 1]")


@dataclass(frozen=True)
class AwbStatus:
    """White-balance metadata of the latest frame; absent values are None.

    This reports applied gains, rather than the gains requested for a later frame.
    ``colour_temperature`` is in kelvin and ``lux`` is in lux.
    """

    gain_r: Optional[float]
    gain_b: Optional[float]
    colour_temperature: Optional[int]
    lux: Optional[float]


AwbSettings = Union[Auto, libcam.controls.AwbModeEnum, AwbManual, AwbGreyWorld]


@dataclass(frozen=True)
class SensorConfig:
    bit_depth: int
    output_size: Tuple[int, int]

    def to_libcamera(self) -> libcam.SensorConfiguration:
        width, height = self.output_size

        sensor = libcam.SensorConfiguration()
        sensor.bit_depth = self.bit_depth
        sensor.output_size = libcam.Size(width, height)
        return sensor


@dataclass(frozen=True)
class ScalerCrop:
    x: int
    y: int
    width: int
    height: int

    def to_libcamera(self) -> libcam.Rectangle:
        return libcam.Rectangle(self.x, self.y, self.width, self.height)


class CameraConfigurationInvalidError(Exception):
    _config: libcam.CameraConfiguration
    _msg: str

    def __init__(self, config: libcam.CameraConfiguration, msg: str = "Invalid CameraConfiguration"):
        super().__init__(msg)
        self._config = config
        self._msg = msg

    def __str__(self) -> str:
        return f"{self._msg}: {self._config}"


class CameraConfigureError(Exception):
    _errno: int
    _msg: str

    def __init__(self, errno: int, msg: str = "Camera configure failed"):
        super().__init__(msg)
        self._errno = errno
        self._msg = msg

    def __str__(self) -> str:
        return f"{self._msg}: {self._errno}"


class FrameBufferAllocateError(Exception):
    _errno: int
    _msg: str

    def __init__(self, errno: int, msg: str = "FrameBuffer allocation error"):
        super().__init__(msg)
        self._errno = errno
        self._msg = msg

    def __str__(self) -> str:
        return f"{self._msg}: {self._errno}"


class CameraStartError(Exception):
    _errno: int
    _msg: str

    def __init__(self, errno: int, msg: str = "CameraStart error"):
        super().__init__(msg)
        self._errno = errno
        self._msg = msg

    def __str__(self) -> str:
        return f"{self._msg}: {self._errno}"


class QueueRequestError(Exception):
    _errno: int
    _msg: str

    def __init__(self, errno: int, msg: str = "QueueRequest error"):
        super().__init__(msg)
        self._errno = errno
        self._msg = msg

    def __str__(self) -> str:
        return f"{self._msg}: {self._errno}"


class CaptureTimeoutError(Exception):
    _timeout: int
    _msg: str

    def __init__(self, timeout: int, msg: str = "Capture timeout"):
        super().__init__(msg)
        self._timeout = timeout
        self._msg = msg

    def __str__(self) -> str:
        return f"{self._msg}: {self._timeout}"


def find_csi_camera_index() -> Optional[int]:
    """Return the index of the first CSI camera, or None if there is none. (Raspberry Pi specific.)

    Intended for selecting a single CSI camera. A CSI camera is identified by its ``platform/`` id
    prefix (set by the ``rpi/pisp`` / ``rpi/vc4`` pipeline handler); the location property cannot be
    used since Raspberry Pi CSI cameras report ``Location = External`` just like USB ones. Pass the
    result to ``LibcameraCapture(..., camera_index=...)`` to avoid accidentally picking a USB camera
    that libcamera may also enumerate.

    Note:
        The returned index is not a stable id; it is a position in the libcamera enumeration order
        and may differ between runs, so use it promptly rather than persisting it.
    """
    cm = libcam.CameraManager.singleton()
    for index, camera in enumerate(cm.cameras):
        if str(camera.id).startswith("platform/"):
            return index
    return None


class LibcameraCapture(Producer[Frame[bytes]]):
    _cm: libcam.CameraManager
    _size: Tuple[int, int]
    _pixel_format: libcam.PixelFormat
    _camera: libcam.Camera
    _requests: Optional[List[libcam.Request]]
    _camera_config: libcam.CameraConfiguration
    _framerate: int
    _shutter_time: Union[float, Auto]
    _analogue_gain: Union[float, Auto]
    _depad: bool
    _stride: int
    _scaler_crop: Optional[ScalerCrop]

    def __init__(
        self,
        size: Tuple[int, int],
        pixel_format: libcam.PixelFormat,
        camera_index: int = 0,
        orientation: libcam.Orientation = libcam.Orientation.Rotate0,
        framerate: int = 30,
        depad: bool = True,
        sensor_config: Optional[SensorConfig] = None,
        scaler_crop: Optional[ScalerCrop] = None,
        awb: AwbSettings = Auto.AUTO,
    ) -> None:
        """
        Initialization method for the LibcameraCapture class.

        Args:
            size: The size of the captured image (width, height).
            pixel_format: The pixel format. Only RGB888 or BGR888 are supported.
                cf. https://libcamera.org/api-html/classlibcamera_1_1PixelFormat.html
            camera_index: The index of the camera to use. Defaults to 0.
                See ``find_csi_camera_index()`` to select the CSI camera when a USB camera is also connected.
            orientation: The orientation of the camera. Defaults to Rotate0.
                cf. https://libcamera.org/api-html/namespacelibcamera.html#a80ea01625b93ecfe879249ac60c79384.
            framerate: The framerate (fps). If not specified, the default setting of the libcamera is used.
            depad: Whether to strip the per-line stride padding from captured frames. Defaults to True.
                The ISP may pad each line of the output buffer up to an alignment boundary
                (e.g. 64 bytes on Raspberry Pi 5 / PiSP), so the stride can be larger than ``width * 3``.
                When True, the padding is removed and a tightly packed (``width * 3`` per line) buffer is
                produced, so consumers can read it as a plain ``width x height x 3`` image regardless of
                the capture width. When False, the raw buffer is passed through unchanged; in that case use
                ``stride()`` to interpret it yourself (this avoids the per-line depadding repack and is useful
                when you can handle padded strides).
            sensor_config: The sensor configuration used to adjust the field of view. See the libcamera
                documentation for details about sensor configuration.
            scaler_crop: The scaler crop rectangle used to adjust the field of view. See the libcamera
                documentation for details about ``ScalerCrop``.
            awb: White balance: ``Auto.AUTO`` (the unchanged libcamera default),
                ``libcam.controls.AwbModeEnum`` (automatic AWB with an illuminant range),
                ``AwbManual(gain_r, gain_b)``, or ``AwbGreyWorld(gain_r=1.6, gain_b=1.6, k=0.45)``.
                Can also be changed while capturing via ``set_awb_settings()``.

        Note:
            As for pixel_format, if RGB888 is specified, BGR888 is actually obtained,
                and if BGR888 is specified, RGB888 is actually obtained.

        Raises:
            AssertionError: Raised if an unsupported pixel format is specified.
            CameraConfigurationInvalidError: Raised if the camera configuration is invalid.
            CameraConfigureError: Raised if the camera configuration fails.
        """
        try:
            firmware_type = get_actcast_firmware_type()
            if firmware_type != "raspberrypi-bookworm":
                raise RuntimeError("LibcameraCapture is only available in ActcastOS4 or later.")
        except EnvironmentVariableNotSet:
            # No error for when running on Raspberry Pi OS
            pass
        assert pixel_format == libcam.PixelFormat("RGB888") or pixel_format == libcam.PixelFormat("BGR888"), (
            "Only RGB888 or BGR888 are supported"
        )
        super().__init__()
        self._awb_pending: Deque[AwbSettings] = deque(maxlen=1)
        # Only the capture thread changes the active settings and target.
        self._awb_settings: AwbSettings = Auto.AUTO
        self._awb_configured = False
        self._awb_target: Optional[Tuple[float, float]] = None
        self._awb_status: Optional[AwbStatus] = None
        if awb is not Auto.AUTO:
            self.set_awb_settings(awb)
        self._cm = libcam.CameraManager.singleton()
        self._size = size
        self._pixel_format = pixel_format
        self._framerate = framerate
        self._shutter_time = Auto.AUTO
        self._analogue_gain = Auto.AUTO
        self._depad = depad
        self._scaler_crop = scaler_crop
        self._camera = self._cm.cameras[camera_index]
        self._camera.acquire()
        self._camera_config = self._camera.generate_configuration([libcam.StreamRole.Viewfinder])
        self._camera_config.orientation = orientation
        stream_config: libcam.StreamConfiguration = self._camera_config.at(0)
        stream_config.size = libcam.Size(*self._size)
        stream_config.pixel_format = self._pixel_format

        if sensor_config is not None:
            self._camera_config.sensor_config = sensor_config.to_libcamera()

        res = self._camera_config.validate()
        if res == libcam.CameraConfiguration.Status.Invalid:
            raise CameraConfigurationInvalidError(self._camera_config)
        res = self._camera.configure(self._camera_config)
        if res is not None and res < 0:
            raise CameraConfigureError(res)
        # The validated stride (bytes per line, including any padding the ISP adds).
        self._stride = self._camera_config.at(0).stride

    def cameras(self) -> List[libcam.Camera]:
        return self._cm.cameras  # type: ignore

    def capture_size(self) -> Tuple[int, int]:
        stream_config: libcam.StreamConfiguration = self._camera_config.at(0)
        return (stream_config.size.width, stream_config.size.height)

    def stride(self) -> int:
        """Return the stride (bytes per line) of the captured buffer, including padding.

        The ISP may align each line of the output buffer up to a boundary (e.g. 64 bytes on
        Raspberry Pi 5 / PiSP), so this can be larger than ``width * 3``. When the capture is
        created with ``depad=False``, use this together with ``capture_size()`` to interpret
        the raw frame buffer (e.g. ``Image.frombuffer(..., "raw", "RGB", stride, 1)`` for PIL,
        or ``numpy.lib.stride_tricks.as_strided`` for a zero-copy ndarray view).
        """
        return self._stride

    def set_exposure_settings(self, shutter_time: Union[float, Auto], analogue_gain: Union[float, Auto]) -> None:
        """Set shutter_time and analogue_gain.

        Must be called before the capture task is started (i.e. before ``run()``),
        since the controls are applied at ``camera.start()``.

        Args:
            shutter_time (float or Auto): [μsec] (e.g. 60000). If set to Auto, shutter_time is set with AE algorithm.
            analogue_gain (float or Auto): (>=1.0) (e.g. 2.5). If set to Auto, analogue_gain is set with AE algorithm.
        """
        self._shutter_time = shutter_time
        self._analogue_gain = analogue_gain

    def set_awb_settings(self, awb: AwbSettings) -> None:
        """Queue white-balance settings before or during capture.

        Accepts the same values as the constructor's ``awb`` argument. The capture
        thread takes the latest queued settings at camera start or at the beginning
        of the next completed-frame processing. Changes queued during a frame's
        processing wait until the next frame. Controls can take several frames to
        appear in ``awb_status()``. Selecting ``AwbGreyWorld`` resets its target to
        the supplied initial gains when the queued settings are taken. Only one
        pending setting is kept; a new setting replaces the previous pending one.
        """
        if not isinstance(awb, (Auto, libcam.controls.AwbModeEnum, AwbManual, AwbGreyWorld)):
            raise TypeError("awb must be Auto.AUTO, AwbModeEnum, AwbManual, or AwbGreyWorld")
        self._awb_pending.append(awb)

    def _apply_pending_awb_settings(self) -> None:
        """Called only by the capture thread, between frame processing steps."""
        try:
            awb = self._awb_pending.popleft()
        except IndexError:
            return
        self._awb_settings = awb
        self._awb_configured = True
        self._awb_target = (awb.gain_r, awb.gain_b) if isinstance(awb, AwbGreyWorld) else None

    def awb_status(self) -> Optional[AwbStatus]:
        """Return metadata of the latest completed frame, or None before the first frame.

        The returned immutable snapshot may be read from another thread.
        """
        return self._awb_status

    def _awb_controls(self, awb: AwbSettings) -> Dict[Any, Any]:
        if isinstance(awb, Auto):
            # Preserve the existing camera defaults when AWB was not specified.
            if not self._awb_configured:
                return {}
            return {libcam.controls.AwbEnable: True, libcam.controls.AwbMode: libcam.controls.AwbModeEnum.Auto}
        if isinstance(awb, libcam.controls.AwbModeEnum):
            return {libcam.controls.AwbEnable: True, libcam.controls.AwbMode: awb}
        gains = (awb.gain_r, awb.gain_b) if isinstance(awb, AwbManual) else self._awb_target
        return {libcam.controls.AwbEnable: False, libcam.controls.ColourGains: gains}

    def _update_awb(self, frame: bytes, metadata: Dict[Any, Any], awb: AwbSettings) -> None:
        """Record applied metadata and update feedback for the selected AWB mode.

        ``awb`` is selected at the start of this frame's processing and is also
        used to generate controls for requeueing. Metadata describes this completed
        frame, which may still reflect older settings due to controls latency.
        Auto/AwbModeEnum are handled by libcamera and AwbManual uses fixed gains;
        only AwbGreyWorld computes feedback from the output image.
        """
        gains = metadata.get(libcam.controls.ColourGains)
        gain_r, gain_b = (float(gains[0]), float(gains[1])) if gains is not None else (None, None)
        temperature = metadata.get(libcam.controls.ColourTemperature)
        lux = metadata.get(libcam.controls.Lux)
        # Publish a complete immutable snapshot for readers on other threads.
        self._awb_status = AwbStatus(
            gain_r, gain_b, int(temperature) if temperature is not None else None, float(lux) if lux is not None else None
        )
        if isinstance(awb, AwbGreyWorld):
            self._update_greyworld(frame, self._awb_status, awb)

    def _update_greyworld(self, frame: bytes, status: AwbStatus, settings: AwbGreyWorld) -> None:
        """Update the next target using applied gains and the selected damping.

        Initial gains in ``settings`` are used only when the settings are taken
        from the queue. Feedback uses ``status`` gains from the completed frame.
        """
        gain_r, gain_b = status.gain_r, status.gain_b
        target = self._awb_target
        if target is None or gain_r is None or gain_b is None:
            return
        # Older requests remain in flight after setting gains. Never compute
        # another correction until the preceding target appears in metadata.
        applied = (gain_r, gain_b)
        if not all(math.isfinite(g) and abs(g - t) < 1e-3 * max(1.0, t) for g, t in zip(applied, target)):
            return
        width, height = self.capture_size()
        stride = width * 3 if self._depad else self._stride
        # libcamera's BGR888 is RGB in memory; RGB888 is BGR in memory.
        red, blue = (0, 2) if self._pixel_format == libcam.PixelFormat("BGR888") else (2, 0)
        sums = [0, 0, 0]
        view = memoryview(frame)
        for y in range(0, height, 8):
            start = y * stride
            end = start + width * 3
            for channel in range(3):
                sums[channel] += sum(view[start + channel : end : 8 * 3])
        # Output pixels already include the applied gain, hence the
        # multiplicative correction rather than an absolute G/R or G/B gain.
        self._awb_target = (
            min(8.0, max(0.5, gain_r * (sums[1] / (sums[red] + 1)) ** settings.k)),
            min(8.0, max(0.5, gain_b * (sums[1] / (sums[blue] + 1)) ** settings.k)),
        )

    def _strip_stride_padding(self, mm: mmap.mmap) -> bytes:
        """Remove the per-line stride padding, returning a tightly packed (width * 3 per line) buffer.

        If the stride already equals ``width * 3`` there is no padding, so the whole buffer is
        returned as-is (a single copy, same as the previous behaviour).
        """
        width, height = self.capture_size()
        packed_bytes_per_line = width * 3
        stride = self._stride
        if stride == packed_bytes_per_line:
            return mm[:]
        if stride < packed_bytes_per_line:
            raise ValueError(f"Invalid stride {stride} for packed line size {packed_bytes_per_line}")
        mv = memoryview(mm)
        out = bytearray(packed_bytes_per_line * height)
        for y in range(height):
            src = y * stride
            dst = y * packed_bytes_per_line
            out[dst : dst + packed_bytes_per_line] = mv[src : src + packed_bytes_per_line]
        return bytes(out)

    def _handle_camera_event(self) -> None:
        reqs = self._cm.get_ready_requests()
        for req in reqs:
            self._apply_pending_awb_settings()
            awb = self._awb_settings
            buffers = req.buffers
            assert len(buffers) == 1
            stream, frame_buffer = next(iter(buffers.items()))
            assert len(frame_buffer.planes) == 1
            plane = next(iter(frame_buffer.planes))

            with mmap.mmap(plane.fd, plane.length, offset=plane.offset) as mm:
                dst = self._strip_stride_padding(mm) if self._depad else mm[:]

            self._update_awb(dst, req.metadata, awb=awb)
            frame = Frame(dst)
            self._outlet(frame)

            req.reuse()
            for control, value in self._awb_controls(awb=awb).items():
                req.set_control(control, value)
            res = self._camera.queue_request(req)
            if res is not None and res < 0:
                raise QueueRequestError(res)

    def run(self) -> None:
        requests = []
        try:
            allocator = libcam.FrameBufferAllocator(self._camera)
            stream = self._camera_config.at(0).stream
            res = allocator.allocate(stream)
            if res < 0:
                raise FrameBufferAllocateError(res)

            buffers = allocator.buffers(stream)
            for buffer in buffers:
                request = self._camera.create_request()
                res = request.add_buffer(stream, buffer)
                assert res is None or res == 0
                requests.append(request)

            controls: Dict[Any, Any] = {}
            frame_duration_limit = int(1_000_000 / self._framerate)
            controls[libcam.controls.FrameDurationLimits] = (frame_duration_limit, frame_duration_limit)

            if self._scaler_crop is not None:
                controls[libcam.controls.ScalerCrop] = self._scaler_crop.to_libcamera()

            manual_shutter = not isinstance(self._shutter_time, Auto)
            manual_gain = not isinstance(self._analogue_gain, Auto)
            if manual_shutter or manual_gain:
                # AeEnable=False is required so that manual values are not
                # overwritten by the AE algorithm.
                controls[libcam.controls.AeEnable] = False
            if manual_shutter:
                controls[libcam.controls.ExposureTime] = int(self._shutter_time)  # type: ignore[arg-type]
            if manual_gain:
                controls[libcam.controls.AnalogueGain] = float(self._analogue_gain)  # type: ignore[arg-type]

            self._apply_pending_awb_settings()
            controls.update(self._awb_controls(awb=self._awb_settings))
            res = self._camera.start(controls=controls)
            if res is not None and res < 0:
                raise CameraStartError(res)

            for request in requests:
                res = self._camera.queue_request(request)
                if res is not None and res < 0:
                    raise QueueRequestError(res)

            sel = selectors.DefaultSelector()
            sel.register(
                self._cm.event_fd,
                selectors.EVENT_READ,
                lambda: self._handle_camera_event(),
            )
            timeout = 1
            while self._is_running():
                events = sel.select(timeout)
                if events == []:
                    raise CaptureTimeoutError(timeout)

                for key, _mask in events:
                    callback = key.data
                    callback()
        finally:
            self._camera.stop()
            self._camera.release()

    def _new_pad(self) -> _PadBase[Frame[bytes]]:
        return _PadDiscardingOld()
