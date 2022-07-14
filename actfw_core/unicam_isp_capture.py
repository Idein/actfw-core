import select
from ctypes import POINTER, cast, sizeof
from typing import List, Tuple

from actfw_core.capture import Frame
from actfw_core.task import Producer
from actfw_core.v4l2.types import bcm2835_isp_stats, v4l2_ext_control
from actfw_core.v4l2.video import (  # type: ignore
    MEDIA_BUS_FMT,
    V4L2_BUF_TYPE,
    V4L2_CID,
    V4L2_MEMORY,
    V4L2_META_FMT,
    V4L2_PIX_FMT,
    RawVideo,
    V4LConverter,
)


class UnicamIspCapture(Producer[Frame[bytes]]):
    def __init__(
        self,
        unicam: str = "/dev/video0",
        unicam_subdev: str = "/dev/v4l-subdev0",
        isp_in: str = "/dev/video13",
        isp_out_high: str = "/dev/video14",
        isp_out_metadata: str = "/dev/video16",
        size: Tuple[int, int] = (640, 480),
        framerate: int = 30,
        expected_format: V4L2_PIX_FMT = V4L2_PIX_FMT.RGB24,
        auto_whitebalance: bool = True,
    ) -> None:
        super().__init__()
        self.dma_buffer_num = 4
        self.isp_out_buffer_num = 4
        self.isp_out_metadata_buffer_num = 2
        self.shared_dma_fds: List[int] = []
        self.unicam = RawVideo(unicam)
        self.unicam_subdev = RawVideo(unicam_subdev)
        self.isp_in = RawVideo(isp_in, v4l2_buf_type=V4L2_BUF_TYPE.VIDEO_OUTPUT)
        self.isp_out_high = RawVideo(isp_out_high)
        self.isp_out_metadata = RawVideo(isp_out_metadata, v4l2_buf_type=V4L2_BUF_TYPE.META_CAPTURE)
        self.do_awb = auto_whitebalance

        (self.expected_width, self.expected_height) = size
        self.expected_pix_format = expected_format
        self.expected_fps = framerate
        # setup
        self.converter = V4LConverter(self.isp_out_high.device_fd)
        self.setup_pipeline()
        self.output_fmt = self.converter.try_convert(
            self.isp_out_high.fmt, self.expected_width, self.expected_height, self.expected_pix_format
        )

        self.request_buffer()

    def setup_pipeline(self) -> None:
        # setup unicam
        if not (self.unicam_subdev.set_vertical_flip(True) and self.unicam_subdev.set_horizontal_flip(True)):
            raise RuntimeError("fail to setup unicam subdevice node")

        self.unicam_subdev.set_subdev_format(self.expected_width, self.expected_height, MEDIA_BUS_FMT.SBGGR10_1X10)
        self.unicam_width = self.unicam_subdev.subdev_fmt.format.width
        self.unicam_height = self.unicam_subdev.subdev_fmt.format.height
        self.unicam_format = V4L2_PIX_FMT.SBGGR10P
        (unicam_width, unicam_height, unicam_format) = self.unicam.set_pix_format(
            self.unicam_width, self.unicam_height, self.unicam_format
        )
        if unicam_width != self.unicam_width or unicam_height != self.unicam_height or unicam_format != self.unicam_format:
            raise RuntimeError("fail to setup unicam device node")
        self.set_unicam_fps()

        # sutup isp_in
        (isp_in_width, isp_in_height, isp_in_format) = self.isp_in.set_pix_format(
            self.unicam_width, self.unicam_height, self.unicam_format
        )
        if isp_in_width != self.unicam_width or isp_in_height != self.unicam_height or isp_in_format != self.unicam_format:
            raise RuntimeError("fail to setup isp input")

        # setup isp_out_high

        # TODO: Ensure that the value of bytesperline is equal to width or appropriate handle padding.
        # One possible solution is to use only width of multiples of 32.
        (isp_out_width, isp_out_height, isp_out_format) = self.isp_out_high.set_pix_format(
            self.expected_width, self.expected_height, self.expected_pix_format
        )

        self.output_fmt = self.converter.try_convert(
            self.isp_out_high.fmt, self.expected_width, self.expected_height, self.expected_pix_format
        )

        # setup isp_out_metadata
        self.isp_out_metadata.set_meta_format(V4L2_META_FMT.BCM2835_ISP_STATS, sizeof(bcm2835_isp_stats))

    def set_unicam_fps(self) -> None:
        ctrls = self.unicam_subdev.get_ext_controls([V4L2_CID.HBLANK, V4L2_CID.PIXEL_RATE])
        hblank = ctrls[0].value
        pixel_late = ctrls[1].value64
        expected_pixel_per_second = pixel_late // self.expected_fps
        expected_line_num = expected_pixel_per_second // (self.unicam_width + hblank)
        expected_vblank = expected_line_num - self.unicam_height
        # TODO: check supported vblank range
        vblank_ctrl = v4l2_ext_control()
        vblank_ctrl.id = V4L2_CID.VBLANK
        vblank_ctrl.value = expected_vblank
        ctrls = self.unicam_subdev.set_ext_controls([vblank_ctrl])

    def capture_size(self) -> Tuple[int, int]:
        return (self.output_fmt.fmt.pix.width, self.output_fmt.fmt.pix.height)

    def request_buffer(self) -> None:
        self.unicam.request_buffers(self.dma_buffer_num, V4L2_MEMORY.MMAP)
        self.dma_fds = self.unicam.export_buffers()
        self.unicam.request_buffers(self.dma_buffer_num, V4L2_MEMORY.DMABUF, self.dma_fds)
        self.isp_in.request_buffers(self.dma_buffer_num, V4L2_MEMORY.DMABUF, self.dma_fds)
        self.isp_out_high.request_buffers(self.isp_out_buffer_num, V4L2_MEMORY.MMAP)
        self.isp_out_metadata.request_buffers(self.isp_out_metadata_buffer_num, V4L2_MEMORY.MMAP)

    def unicam2isp(self) -> None:
        buffer = self.unicam.dequeue_buffer_nonblocking(v4l2_memory=V4L2_MEMORY.DMABUF)
        if buffer is None:
            return
        self.isp_in.queue_buffer(buffer.buf.index)

    def isp2unicam(self) -> None:
        buffer = self.isp_in.dequeue_buffer_nonblocking(v4l2_memory=V4L2_MEMORY.DMABUF)
        if buffer is None:
            return
        self.unicam.queue_buffer(buffer.buf.index)

    def produce_image_from_isp(self) -> None:
        buffer = self.isp_out_high.dequeue_buffer_nonblocking(v4l2_memory=V4L2_MEMORY.MMAP)
        if buffer is None:
            return

        dst = self.converter.convert(buffer, self.isp_out_high.fmt, self.output_fmt)
        frame = Frame(dst)
        self._outlet(frame)
        self.isp_out_high.queue_buffer(buffer.buf.index)

    def adust_setting_from_isp(self) -> None:
        buffer = self.isp_out_metadata.dequeue_buffer_nonblocking(v4l2_memory=V4L2_MEMORY.MMAP)
        if buffer is None:
            return

        stats: bcm2835_isp_stats = cast(buffer.mapped_buf, POINTER(bcm2835_isp_stats)).contents
        if self.do_awb:
            sum_r = 0
            sum_b = 0
            sum_g = 0
            # len(stats.awb_stats) == 192
            for region in stats.awb_stats:
                sum_r += region.r_sum
                sum_b += region.b_sum
                sum_g += region.g_sum

            self.gain_r = sum_g / (sum_r + 1)
            self.gain_b = sum_g / (sum_b + 1)

            red_balance_ctrl = v4l2_ext_control()
            red_balance_ctrl.id = V4L2_CID.RED_BALANCE
            red_balance_ctrl.value64 = int(self.gain_r * 1000)
            blue_balance_ctrl = v4l2_ext_control()
            blue_balance_ctrl.id = V4L2_CID.BLUE_BALANCE
            blue_balance_ctrl.value64 = int(self.gain_b * 1000)
            self.isp_in.set_ext_controls([red_balance_ctrl, blue_balance_ctrl])

        self.isp_out_metadata.queue_buffer(buffer.buf.index)

    def run(self) -> None:
        self.unicam.queue_all_buffers()
        self.isp_out_high.queue_all_buffers()
        self.isp_out_metadata.queue_all_buffers()

        self.unicam.start_streaming()
        self.isp_in.start_streaming()
        self.isp_out_high.start_streaming()
        self.isp_out_metadata.start_streaming()

        class FDWrapper:
            def __init__(self, fd: int) -> None:
                self.fd = fd

            def fileno(self) -> int:
                return self.fd

        while self._is_running():
            timeout = 1
            rlist, wlist, _ = select.select(
                [
                    FDWrapper(self.unicam.device_fd),
                    FDWrapper(self.isp_out_high.device_fd),
                    FDWrapper(self.isp_out_metadata.device_fd),
                ],
                [FDWrapper(self.isp_in.device_fd)],
                [],
                timeout,
            )

            if len(rlist) == 0 and len(wlist) == 0:
                raise RuntimeError("Capture timeout")

            for r in rlist:
                if r.fileno() == self.unicam.device_fd:
                    self.unicam2isp()
                elif r.fileno() == self.isp_out_high.device_fd:
                    self.produce_image_from_isp()
                elif r.fileno() == self.isp_out_metadata.device_fd:
                    self.adust_setting_from_isp()
            for w in wlist:
                if w.fileno() == self.isp_in.device_fd:
                    self.isp2unicam()
