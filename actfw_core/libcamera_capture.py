"""
LibcameraCapture module.

Note:
    This module is only available in ActcastOS4 or later.
"""
import json
import mmap
import selectors
from os import path
from typing import Any, Dict, List, Optional, Tuple

import libcamera as libcam
from actfw_core.autofocus import AutoFocuserBase, Rectangle
from actfw_core.capture import Frame
from actfw_core.system import EnvironmentVariableNotSet, get_actcast_firmware_type
from actfw_core.task import Producer
from actfw_core.util.pad import _PadBase, _PadDiscardingOld


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


class LibcameraCapture(Producer[Frame[bytes]]):
    _cm: libcam.CameraManager
    _size: Tuple[int, int]
    _pixel_format: libcam.PixelFormat
    _camera: libcam.Camera
    _requests: Optional[List[libcam.Request]]
    _camera_config: libcam.CameraConfiguration
    _framerate: int

    def __init__(
        self,
        size: Tuple[int, int],
        pixel_format: libcam.PixelFormat,
        camera_index: int = 0,
        orientation: libcam.Orientation = libcam.Orientation.Rotate0,
        framerate: int = 30,
        auto_focuser: Optional[AutoFocuserBase] = None,
    ) -> None:
        """
        Initialization method for the LibcameraCapture class.

        Args:
            size: The size of the captured image (width, height).
            pixel_format: The pixel format. Only RGB888 or BGR888 are supported.
                cf. https://libcamera.org/api-html/classlibcamera_1_1PixelFormat.html
            camera_index: The index of the camera to use. Defaults to 0.
            orientation: The orientation of the camera. Defaults to Rotate0.
                cf. https://libcamera.org/api-html/namespacelibcamera.html#a80ea01625b93ecfe879249ac60c79384.
            framerate: The framerate (fps). If not specified, the default setting of the libcamera is used.

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
        assert pixel_format == libcam.PixelFormat("RGB888") or pixel_format == libcam.PixelFormat(
            "BGR888"
        ), "Only RGB888 or BGR888 are supported"
        super().__init__()
        self._cm = libcam.CameraManager.singleton()
        self._size = size
        self._pixel_format = pixel_format
        self._framerate = framerate
        self._camera = self._cm.cameras[camera_index]
        self._camera.acquire()
        self._camera_config = self._camera.generate_configuration([libcam.StreamRole.Viewfinder])
        self.auto_focuser = auto_focuser
        self._pending_focus_position: Optional[float] = None
        self._pending_af_controls: Dict = {}
        self._pending_focus_windows: Optional[List] = None
        if self.auto_focuser is not None:
            self._setup_autofocus()
        self._camera_config.orientation = orientation
        stream_config: libcam.StreamConfiguration = self._camera_config.at(0)
        stream_config.size = libcam.Size(*self._size)
        stream_config.pixel_format = self._pixel_format
        res = self._camera_config.validate()
        if res == libcam.CameraConfiguration.Status.Invalid:
            raise CameraConfigurationInvalidError(self._camera_config)
        res = self._camera.configure(self._camera_config)
        if res is not None and res < 0:
            raise CameraConfigureError(res)

    def _get_sensor_name(self) -> str:
        """
        Get sensor name from video device (same logic as unicam implementation).
        """
        try:
            # Try to find sensor name from video devices
            # This is a temporary implementation using same logic as unicam
            import glob

            video_devices = glob.glob("/sys/class/video4linux/video*/device/name")
            for device_path in video_devices:
                try:
                    with open(device_path) as f:
                        sensor_name = f.read().rstrip()
                        # Check if this looks like a sensor name
                        if sensor_name.lower().startswith(("imx", "ov")):
                            return sensor_name
                except OSError:
                    continue
        except Exception:
            pass
        raise RuntimeError("Could not detect sensor name from video devices")

    def _setup_autofocus(self) -> None:
        """
        Setup autofocus configuration for libcamera backend.
        """
        # Get sensor name and load corresponding config file (same as unicam)
        sensor_name = self._get_sensor_name()
        config_file = sensor_name + ".json"

        # Load sensor config from JSON file
        try:
            with open(path.join(path.dirname(__file__), "data", config_file), "r") as f:
                sensor_config = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"not supported sensor: {sensor_name}")
        if self.auto_focuser is not None:
            self.auto_focuser.set_libcamera_config(self._camera, sensor_config, self._size, self._libcamera_focus_callback)

        # Apply initial AfMode control
        from actfw_core.autofocus import AfMode

        afmode_map = {
            AfMode.AfModeManual: libcam.controls.AfModeEnum.Manual,
            AfMode.AfModeAuto: libcam.controls.AfModeEnum.Auto,
            AfMode.AfModeContinuous: libcam.controls.AfModeEnum.Continuous,
        }
        if self.auto_focuser is not None and self.auto_focuser.afmode in afmode_map:
            self._pending_af_controls[libcam.controls.AfMode] = afmode_map[self.auto_focuser.afmode]

    def _convert_focus_windows_to_libcamera(self, windows: List[Rectangle]) -> List[Tuple[int, int, int, int]]:
        """
        Convert focus windows from Rectangle objects to libcamera format.
        windows: List of Rectangle objects from autofocuser
        returns: [(x, y, width, height), ...] in capture coordinates
        """
        libcam_windows = []

        for window in windows:
            x = int(window.x)
            y = int(window.y)
            width = int(window.width)
            height = int(window.height)

            # Ensure positive width/height (libcamera requirement)
            if width > 0 and height > 0:
                libcam_windows.append((x, y, width, height))

        return libcam_windows

    # who call this method?
    def _apply_focus_windows(self, windows: List[Rectangle]) -> None:
        """
        Apply focus windows to libcamera controls.
        """
        if not windows:
            # Clear focus windows
            self._pending_focus_windows = []
            return

        # Convert to libcamera format
        libcam_windows = self._convert_focus_windows_to_libcamera(windows)
        if libcam_windows:
            self._pending_focus_windows = libcam_windows
            # Also set metering mode to use windows
            self._pending_af_controls[libcam.controls.AfMetering] = libcam.controls.AfMeteringEnum.Windows

    def _libcamera_focus_callback(self, lens_position: int) -> None:
        """
        Callback function to handle focus position updates from autofocuser.
        """
        # Store the pending focus control to be applied on next request
        # Convert lens position to libcamera diopters (0.0-12.0 range)
        diopters = max(0.0, min(12.0, lens_position / 100.0))
        self._pending_focus_position = diopters

    def _trigger_libcamera_autofocus(self) -> None:
        """
        Trigger autofocus scan for libcamera backend.
        """
        self._pending_af_controls[libcam.controls.AfTrigger] = libcam.controls.AfTriggerEnum.Start

    def _process_autofocus_metadata(self, metadata: Any) -> None:
        """
        Process autofocus metadata from libcamera and update autofocuser status.
        """
        if not self.auto_focuser:
            return

        from actfw_core.autofocus import AfState, ScanState

        # Map libcamera AfState to our AfState
        if libcam.controls.AfState in metadata:
            libcam_state = metadata[libcam.controls.AfState]
            state_map = {
                libcam.controls.AfStateEnum.Idle: AfState.Idle,
                libcam.controls.AfStateEnum.Scanning: AfState.Scanning,
                libcam.controls.AfStateEnum.Focused: AfState.Focused,
                libcam.controls.AfStateEnum.Failed: AfState.Failed,
            }
            if libcam_state in state_map:
                self.auto_focuser.afstatus.state = state_map[libcam_state]

                # Reset scan_state when AF is complete (focused or failed)
                if libcam_state in [libcam.controls.AfStateEnum.Focused, libcam.controls.AfStateEnum.Failed]:
                    self.auto_focuser.scan_state = ScanState.Idle

        # Update lens position from metadata
        if libcam.controls.LensPosition in metadata:
            diopters = metadata[libcam.controls.LensPosition]
            # Convert diopters back to lens position (reverse of callback conversion)
            lens_position = int(diopters * 100)
            self.auto_focuser.afstatus.lensSetting = lens_position

    def cameras(self) -> List[libcam.Camera]:
        return self._cm.cameras  # type: ignore

    def capture_size(self) -> Tuple[int, int]:
        stream_config: libcam.StreamConfiguration = self._camera_config.at(0)
        return (stream_config.size.width, stream_config.size.height)

    def _handle_camera_event(self) -> None:
        reqs = self._cm.get_ready_requests()
        for req in reqs:
            # Process autofocus metadata if available
            if req.metadata and self.auto_focuser:
                self._process_autofocus_metadata(req.metadata)
            buffers = req.buffers
            assert len(buffers) == 1
            stream, frame_buffer = next(iter(buffers.items()))
            assert len(frame_buffer.planes) == 1
            plane = next(iter(frame_buffer.planes))

            with mmap.mmap(plane.fd, plane.length, offset=plane.offset) as mm:
                dst = mm[:]

            frame = Frame(dst)
            self._outlet(frame)

            # Process autofocus controls if enabled
            if self.auto_focuser is not None:
                # Check for AF trigger requests
                from actfw_core.autofocus import ScanState

                if self.auto_focuser.scan_state == ScanState.Trigger:
                    self._pending_af_controls[libcam.controls.AfTrigger] = libcam.controls.AfTriggerEnum.Start
                    self.auto_focuser.scan_state = ScanState.Settle

                # Check for focus window updates
                if getattr(self.auto_focuser, "is_pending_window_update", False):
                    libcam_windows = self._convert_focus_windows_to_libcamera(self.auto_focuser.windows)
                    if libcam_windows:
                        self._pending_af_controls[libcam.controls.AfWindows] = libcam_windows
                        self._pending_af_controls[libcam.controls.AfMetering] = libcam.controls.AfMeteringEnum.Windows
                    else:
                        # Clear windows if empty
                        self._pending_af_controls[libcam.controls.AfMetering] = libcam.controls.AfMeteringEnum.Auto
                    self.auto_focuser.is_pending_window_update = False

            # Apply pending focus controls to the request before reuse
            if self._pending_focus_position is not None:
                req.controls[libcam.controls.LensPosition] = self._pending_focus_position
                self._pending_focus_position = None

            # Apply other pending AF controls
            if self._pending_af_controls:
                req.controls.update(self._pending_af_controls)
                self._pending_af_controls.clear()

            req.reuse()
            self._camera.queue_request(req)

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

            controls = {}
            frame_duration_limit = int(1_000_000 / self._framerate)
            controls[libcam.controls.FrameDurationLimits] = (frame_duration_limit, frame_duration_limit)
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
