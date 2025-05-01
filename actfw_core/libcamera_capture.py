import mmap
import selectors
from typing import List, Optional, Tuple

import libcamera as libcam
from actfw_core.capture import Frame
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
    _framerate: Optional[int]

    def __init__(
        self,
        size: Tuple[int, int],
        pixel_format: libcam.PixelFormat,
        camera_index: int = 0,
        orientation: libcam.Orientation = libcam.Orientation.Rotate0,
        framerate: Optional[int] = None,
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

    def cameras(self) -> List[libcam.Camera]:
        return self._cm.cameras  # type: ignore

    def capture_size(self) -> Tuple[int, int]:
        stream_config: libcam.StreamConfiguration = self._camera_config.at(0)
        return (stream_config.size.width, stream_config.size.height)

    def _handle_camera_event(self) -> None:
        reqs = self._cm.get_ready_requests()
        for req in reqs:
            buffers = req.buffers
            assert len(buffers) == 1
            stream, frame_buffer = next(iter(buffers.items()))
            assert len(frame_buffer.planes) == 1
            plane = next(iter(frame_buffer.planes))

            with mmap.mmap(plane.fd, plane.length, offset=plane.offset) as mm:
                dst = mm[:]

            frame = Frame(dst)
            self._outlet(frame)

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
            if self._framerate is not None:
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
