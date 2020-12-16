import io
from queue import Full
from .task import Producer
from actfw_core.v4l2.video import Video, VideoPort, V4L2_PIX_FMT
import enum


class Frame(object):

    """Captured Frame"""

    def __init__(self, value):
        self.value = value
        self.updatable = True

    def getvalue(self):
        """
        Get frame data.

        Returns:
            bytes: captured image data

        """
        self.updatable = False
        return self.value

    def _update(self, value):
        if self.updatable:
            self.value = value
            return True
        return False


class V4LCameraCapture(Producer):

    FormatSelector = enum.Enum('FormatSelector', 'DEFAULT PROPER')

    """Captured Frame Producer for Video4Linux"""

    def __init__(self, device='/dev/video0', size=(640, 480), framerate=30,
                 expected_format=V4L2_PIX_FMT.RGB24,
                 fallback_formats=[V4L2_PIX_FMT.YUYV, V4L2_PIX_FMT.MJPEG],
                 format_selector=FormatSelector.DEFAULT):
        """

        Args:
            device (str): v4l device path
            size (int, int): expected capture resolution
            framerate (int): expected capture framerate
            expected_format (:class:`~actfw_core.v4l2.video.V4L2_PIX_FMT`): expected capture format
            fallback_formats (list of :class:`~actfw_core.v4l2.video.V4L2_PIX_FMT`): fallback capture format

        Notes:
            If a camera doesn't support the expected_format,
            try to capture one of the fallback_formats and convert it to expected_format.

        """
        super(V4LCameraCapture, self).__init__()
        self.video = Video(device)
        self.frames = []

        width, height = size

        if self.video.query_capability() == VideoPort.CSI:

            # workaround for bcm2835-v4l2 format pixsize & bytesperline bug
            width = (width + 31) // 32 * 32
            height = (height + 15) // 16 * 16

            # workaround for bcm2835-v4l2 IMX219 32x32 -> 800x800 capture timeout bug
            candidates = self.video.lookup_config(64, 64, 5, V4L2_PIX_FMT.RGB24, V4L2_PIX_FMT.RGB24)
            self.video.set_format(candidates[0], 64, 64, V4L2_PIX_FMT.RGB24)

        if format_selector == V4LCameraCapture.FormatSelector.PROPER:
            def cmp(config):
                return (
                    config.width * config.height,
                    config.height,
                    config.width,
                    config.interval.denominator / config.interval.numerator
                )
        else:
            def cmp(config):
                return 1
        config = None
        fmts = [expected_format] + fallback_formats
        for fmt in fmts:
            candidates = self.video.lookup_config(width, height, framerate, fmt, expected_format)
            candidates = sorted(candidates, key=cmp)
            if len(candidates) > 0:
                config = candidates[0]
                break
        if config is None:
            raise RuntimeError("expected capture format is unsupported")
        fmt = self.video.set_format(config, width, height, expected_format)
        self.capture_width, self.capture_height, self.capture_format = fmt
        self.video.set_framerate(config)
        # video.set_rotation(90)
        buffers = self.video.request_buffers(4)
        for buf in buffers:
            self.video.queue_buffer(buf)

    def capture_size(self):
        """
        Get configured capture resolution.
        A configured resolution may be more larger than expected one.

        Returns:
            (int, int): configured capture resolution (width, height)
        """
        return (self.capture_width, self.capture_height)

    def configure(self, configurator):
        """
        Run user defined video configurator.

        Args:
            configurator : unary function (`actfw_core.v4l2.video.Video` -> a)

        Returns:
            object: return type of configurator
        """
        return configurator(self.video)

    def run(self):
        """Run producer activity"""
        with self.video.start_streaming() as stream:
            while self._is_running():
                try:
                    value = stream.capture(timeout=5)
                    updated = 0
                    for frame in reversed(self.frames):
                        if frame._update(value):
                            updated += 1
                        else:
                            break
                    self.frames = self.frames[len(self.frames) - updated:]
                    frame = Frame(value)
                    if self._outlet(frame):
                        self.frames.append(frame)
                except:
                    raise
        self.video.close()

    def _outlet(self, o):
        length = len(self.out_queues)
        while self._is_running():
            try:
                self.out_queues[self.out_queue_id % length].put(o, block=False)
                self.out_queue_id += 1
                return True
            except Full:
                return False
            except:
                traceback.print_exc()
        return False
