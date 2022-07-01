from actfw_core.v4l2.video import *
from typing import Generic, Tuple, TypeVar
from actfw_core.task import Producer
import time


T = TypeVar("T")


class Frame(Generic[T]):
    value: T

    """Captured Frame"""

    def __init__(self, value: T) -> None:
        self.value = value

    def getvalue(self) -> T:
        """
        Get frame data.

        Returns:
            bytes: captured image data

        """
        return self.value




class FDWrapper:
    def __init__(self, fd):
        self.fd = fd
    def fileno(self):
        return self.fd


class UnicamIspCapture(Producer[Frame[bytes]]):

    def __init__(
        self, 
        unicam: str = "/dev/video0",
        unicam_subdev: str = "/dev/v4l-subdev0",
        isp_in: str = "/dev/video13", 
        isp_out_high: str = "/dev/video14",
        size: Tuple[int, int] = (640, 480),
        framerate: int = 30,
        expected_format: V4L2_PIX_FMT = V4L2_PIX_FMT.YUV420,        
        ):
        super().__init__()
        self.dma_buffer_num = 4
        self.isp_out_buffer_num = 4
        self.shared_dma_fds = []
        self.unicam = RawVideo(unicam)
        self.unicam_subdev = RawVideo(unicam_subdev)
        self.isp_in = RawVideo(isp_in, v4l2_buf_type=V4L2_BUF_TYPE.VIDEO_OUTPUT)
        self.isp_out_high = RawVideo(isp_out_high)

        
        (self.expected_width, self.expected_height) = size
        self.expected_pix_format = expected_format
        self.expected_fps = framerate
        # setup
        self.converter = V4LConverter(self.isp_out_high.device_fd)
        self.setup_pipeline()
        self.output_fmt = self.converter.try_convert(self.isp_out_high.fmt, self.expected_width, self.expected_height, self.expected_pix_format)

        self.request_buffer()

    def setup_pipeline(self):
        # setup subdev
        # TODO: capability見て最適なsize選択
        self.unicam_subdev.set_subdev_format(self.expected_width, (self.expected_height), MEDIA_BUS_FMT.SBGGR10_1X10)
        self.unicam_width = self.unicam_subdev.subdev_fmt.format.width
        self.unicam_height = self.unicam_subdev.subdev_fmt.format.height
        self.unicam_format = V4L2_PIX_FMT.SBGGR10P
        (unicam_width, unicam_height, unicam_format) = self.unicam.set_format(self.unicam_width, self.unicam_height, self.unicam_format)
        assert(unicam_width == self.unicam_width)
        assert(unicam_height == self.unicam_height)        
        assert(unicam_format == self.unicam_format)

        # fps
        ctrls = self.unicam_subdev.get_ext_controls([V4L2_CID.HBLANK, V4L2_CID.PIXEL_RATE])
        hblank = ctrls[0].value
        pixel_late = ctrls[1].value64

        expected_pixel_per_second = pixel_late // self.expected_fps
        expected_line_num = expected_pixel_per_second // (self.unicam_width + hblank)
        expected_vblank = expected_line_num - self.unicam_height

        # TODO: vblankで設定できるmin/maxを確認する
        vblank_ctrl = v4l2_ext_control()
        vblank_ctrl.id = V4L2_CID.VBLANK
        vblank_ctrl.value = expected_vblank
        ctrls = self.unicam_subdev.set_ext_controls([vblank_ctrl])

        # sutup isp-in
        (isp_in_width, isp_in_height, isp_in_format) = self.isp_in.set_format(self.unicam_width, self.unicam_height, self.unicam_format)
        assert(isp_in_width == self.unicam_width)
        assert(isp_in_height == self.unicam_height)        
        assert(isp_in_format == self.unicam_format)

        # setup isp_out_high
        (isp_out_width, isp_out_height, isp_out_format) = self.isp_out_high.set_format(self.expected_width, self.expected_height, self.expected_pix_format)



    def request_buffer(self):
        self.unicam.request_buffers(self.dma_buffer_num, V4L2_MEMORY.MMAP)
        self.dma_fds = self.unicam.export_buffers()
        self.unicam.request_buffers(self.dma_buffer_num, V4L2_MEMORY.DMABUF, self.dma_fds)
        self.isp_in.request_buffers(self.dma_buffer_num, V4L2_MEMORY.DMABUF, self.dma_fds)
        self.isp_out_high.request_buffers(self.isp_out_buffer_num, V4L2_MEMORY.MMAP)
    

    def unicam2isp(self):
        buffer = self.unicam.dequeue_buffer_nonblocking(v4l2_memory=V4L2_MEMORY.DMABUF)
        if buffer is None:
            return
        self.isp_in.queue_buffer(buffer.buf.index)

    def isp2unicam(self):
        buffer = self.isp_in.dequeue_buffer_nonblocking(v4l2_memory=V4L2_MEMORY.DMABUF)
        if buffer is None:
            return
        self.unicam.queue_buffer(buffer.buf.index)        

    def produceImageFromIsp(self):
        buffer = self.isp_out_high.dequeue_buffer_nonblocking(v4l2_memory=V4L2_MEMORY.DMABUF)
        if buffer is None:
            return
        
        dst = self.converter.convert(buffer, self.isp_out_high.fmt, self.output_fmt)
        frame = Frame(dst)
        self._outlet(frame)
        self.isp_out_high.queue_buffer(buffer.buf.index)        


    def run(self):
        self.unicam.queue_all_buffers()
        self.isp_out_high.queue_all_buffers()

        self.unicam.start_streaming()
        self.isp_in.start_streaming()        
        self.isp_out_high.start_streaming()        
        
        while self._is_running():
            timeout = 1
            rlist, wlist, _ = select.select([FDWrapper(self.unicam.device_fd), FDWrapper(self.isp_out_high.device_fd)], [FDWrapper(self.isp_in.device_fd)], [], timeout)
            
            if len(rlist) == 0 and len(wlist) == 0:
                raise RuntimeError("Capture timeout")
            
            for r in rlist:
                if r.fileno() == self.unicam.device_fd:
                    self.unicam2isp()
                elif r.fileno() == self.isp_out_high.device_fd:
                    self.produceImageFromIsp()
            for w in wlist:
                if w.fileno() == self.isp_in.device_fd:
                    self.isp2unicam()

if __name__ == "__main__":
    print("Hello")
    capture = UnicamIspCapture(framerate=50)
    capture.start()
    time.sleep(5)
    capture.stop()

