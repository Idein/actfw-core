# type: ignore
# flake8: noqa

import enum
import errno
import io
import itertools
import mmap
import os
import select
from ctypes import *
from ctypes.util import find_library

from actfw_core.v4l2.control import *
from actfw_core.v4l2.types import *


class _libv4l2(object):
    def __init__(self):
        self.lib = None
        path = find_library("v4l2")
        if path is not None:
            self.lib = CDLL(path, use_errno=True)

    def ioctl(self, *args, **kwargs):
        if self.lib is None:
            raise FileNotFoundError("Not found: 'libv4l2.so'")
        return self.lib.v4l2_ioctl(*args, **kwargs)

    def mmap(self, *args, **kwargs):
        if self.lib is None:
            raise FileNotFoundError("Not found: 'libv4l2.so'")
        return self.lib.v4l2_mmap(*args, **kwargs)

    def munmap(self, *args, **kwargs):
        if self.lib is None:
            raise FileNotFoundError("Not found: 'libv4l2.so'")
        return self.lib.v4l2_munmap(*args, **kwargs)


class _libv4lconvert(object):
    def __init__(self):
        self.lib = None
        path = find_library("v4lconvert")
        if path is not None:
            self.lib = CDLL(path, use_errno=True)

    def create(self, *args, **kwargs):
        if self.lib is None:
            raise FileNotFoundError("Not found: 'libv4lconvert.so'")
        return self.lib.v4lconvert_create(*args, **kwargs)

    def convert(self, *args, **kwargs):
        if self.lib is None:
            raise FileNotFoundError("Not found: 'libv4lconvert.so'")
        return self.lib.v4lconvert_convert(*args, **kwargs)

    def try_format(self, *args, **kwargs):
        if self.lib is None:
            raise FileNotFoundError("Not found: 'libv4lconvert.so'")
        return self.lib.v4lconvert_try_format(*args, **kwargs)


_v4l2 = _libv4l2()
_v4lconvert = _libv4lconvert()

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8

_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRMASK = (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK = (1 << _IOC_TYPEBITS) - 1
_IOC_SIZEMASK = (1 << _IOC_SIZEBITS) - 1
_IOC_DIRMASK = (1 << _IOC_DIRBITS) - 1

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2


def _IOC(dir, type, nr, size):
    return (dir << _IOC_DIRSHIFT) | (ord(type) << _IOC_TYPESHIFT) | (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT)


def _IO(type, nr):
    return _IOC(_IOC_NONE, type, nr, 0)


def _IOR(type, nr, size):
    return _IOC(_IOC_READ, type, nr, sizeof(size))


def _IOW(type, nr, size):
    return _IOC(_IOC_WRITE, type, nr, sizeof(size))


def _IOWR(type, nr, size):
    return _IOC(_IOC_READ | _IOC_WRITE, type, nr, sizeof(size))


class _VIDIOC(enum.IntEnum):
    QUERYCAP = _IOR("V", 0, capability)
    ENUM_FMT = _IOWR("V", 2, fmtdesc)
    S_FMT = _IOWR("V", 5, format)
    REQBUFS = _IOWR("V", 8, requestbuffers)
    QUERYBUF = _IOWR("V", 9, buffer)
    QBUF = _IOWR("V", 15, buffer)
    DQBUF = _IOWR("V", 17, buffer)
    STREAMON = _IOW("V", 18, c_int)
    STREAMOFF = _IOW("V", 19, c_int)
    S_PARM = _IOWR("V", 22, streamparm)
    G_CTRL = _IOWR("V", 27, control)
    S_CTRL = _IOWR("V", 28, control)
    QUERYCTRL = _IOWR("V", 36, queryctrl)
    ENUM_FRAMESIZES = _IOWR("V", 74, frmsizeenum)
    ENUM_FRAMEINTERVALS = _IOWR("V", 75, frmivalenum)


_V4L2_CAP_VIDEO_CAPTURE = 0x00000001
_V4L2_CAP_VIDEO_OUTPUT = 0x00000002
_V4L2_CAP_VIDEO_OVERLAY = 0x00000004
_V4L2_CAP_VBI_CAPTURE = 0x00000010
_V4L2_CAP_VBI_OUTPUT = 0x00000020
_V4L2_CAP_SLICED_VBI_CAPTURE = 0x00000040
_V4L2_CAP_SLICED_VBI_OUTPUT = 0x00000080
_V4L2_CAP_RDS_CAPTURE = 0x00000100
_V4L2_CAP_VIDEO_OUTPUT_OVERLAY = 0x00000200
_V4L2_CAP_HW_FREQ_SEEK = 0x00000400
_V4L2_CAP_RDS_OUTPUT = 0x00000800
_V4L2_CAP_VIDEO_CAPTURE_MPLANE = 0x00001000
_V4L2_CAP_VIDEO_OUTPUT_MPLANE = 0x00002000
_V4L2_CAP_VIDEO_M2M_MPLANE = 0x00004000
_V4L2_CAP_VIDEO_M2M = 0x00008000
_V4L2_CAP_TUNER = 0x00010000
_V4L2_CAP_AUDIO = 0x00020000
_V4L2_CAP_RADIO = 0x00040000
_V4L2_CAP_MODULATOR = 0x00080000
_V4L2_CAP_SDR_CAPTURE = 0x00100000
_V4L2_CAP_EXT_PIX_FORMAT = 0x00200000
_V4L2_CAP_SDR_OUTPUT = 0x00400000
_V4L2_CAP_READWRITE = 0x01000000
_V4L2_CAP_ASYNCIO = 0x02000000
_V4L2_CAP_STREAMING = 0x04000000
_V4L2_CAP_TOUCH = 0x10000000
_V4L2_CAP_DEVICE_CAPS = 0x80000000


def _fourcc(a, b, c, d):
    return ord(a) | (ord(b) << 8) | (ord(c) << 16) | (ord(d) << 24)


def _fourcc_be(a, b, c, d):
    return _fourcc(a, b, c, d) | (1 << 31)


class V4L2_PIX_FMT(enum.IntEnum):
    RGB332 = _fourcc("R", "G", "B", "1")
    RGB444 = _fourcc("R", "4", "4", "4")
    ARGB444 = _fourcc("A", "R", "1", "2")
    XRGB444 = _fourcc("X", "R", "1", "2")
    RGB555 = _fourcc("R", "G", "B", "O")
    ARGB555 = _fourcc("A", "R", "1", "5")
    XRGB555 = _fourcc("X", "R", "1", "5")
    RGB565 = _fourcc("R", "G", "B", "P")
    RGB555X = _fourcc("R", "G", "B", "Q")
    ARGB555X = _fourcc_be("A", "R", "1", "5")
    XRGB555X = _fourcc_be("X", "R", "1", "5")
    RGB565X = _fourcc("R", "G", "B", "R")
    BGR666 = _fourcc("B", "G", "R", "H")
    BGR24 = _fourcc("B", "G", "R", "3")
    RGB24 = _fourcc("R", "G", "B", "3")
    BGR32 = _fourcc("B", "G", "R", "4")
    ABGR32 = _fourcc("A", "R", "2", "4")
    XBGR32 = _fourcc("X", "R", "2", "4")
    RGB32 = _fourcc("R", "G", "B", "4")
    ARGB32 = _fourcc("B", "A", "2", "4")
    XRGB32 = _fourcc("B", "X", "2", "4")
    GREY = _fourcc("G", "R", "E", "Y")
    Y4 = _fourcc("Y", "0", "4", " ")
    Y6 = _fourcc("Y", "0", "6", " ")
    Y10 = _fourcc("Y", "1", "0", " ")
    Y12 = _fourcc("Y", "1", "2", " ")
    Y16 = _fourcc("Y", "1", "6", " ")
    Y16_BE = _fourcc_be("Y", "1", "6", " ")
    Y10BPACK = _fourcc("Y", "1", "0", "B")
    PAL8 = _fourcc("P", "A", "L", "8")
    UV8 = _fourcc("U", "V", "8", " ")
    YUYV = _fourcc("Y", "U", "Y", "V")
    YYUV = _fourcc("Y", "Y", "U", "V")
    YVYU = _fourcc("Y", "V", "Y", "U")
    UYVY = _fourcc("U", "Y", "V", "Y")
    VYUY = _fourcc("V", "Y", "U", "Y")
    Y41P = _fourcc("Y", "4", "1", "P")
    YUV444 = _fourcc("Y", "4", "4", "4")
    YUV555 = _fourcc("Y", "U", "V", "O")
    YUV565 = _fourcc("Y", "U", "V", "P")
    YUV32 = _fourcc("Y", "U", "V", "4")
    HI240 = _fourcc("H", "I", "2", "4")
    HM12 = _fourcc("H", "M", "1", "2")
    M420 = _fourcc("M", "4", "2", "0")
    NV12 = _fourcc("N", "V", "1", "2")
    NV21 = _fourcc("N", "V", "2", "1")
    NV16 = _fourcc("N", "V", "1", "6")
    NV61 = _fourcc("N", "V", "6", "1")
    NV24 = _fourcc("N", "V", "2", "4")
    NV42 = _fourcc("N", "V", "4", "2")
    NV12M = _fourcc("N", "M", "1", "2")
    NV21M = _fourcc("N", "M", "2", "1")
    NV16M = _fourcc("N", "M", "1", "6")
    NV61M = _fourcc("N", "M", "6", "1")
    NV12MT = _fourcc("T", "M", "1", "2")
    NV12MT_16X16 = _fourcc("V", "M", "1", "2")
    YUV410 = _fourcc("Y", "U", "V", "9")
    YVU410 = _fourcc("Y", "V", "U", "9")
    YUV411P = _fourcc("4", "1", "1", "P")
    YUV420 = _fourcc("Y", "U", "1", "2")
    YVU420 = _fourcc("Y", "V", "1", "2")
    YUV422P = _fourcc("4", "2", "2", "P")
    YUV420M = _fourcc("Y", "M", "1", "2")
    YVU420M = _fourcc("Y", "M", "2", "1")
    YUV422M = _fourcc("Y", "M", "1", "6")
    YVU422M = _fourcc("Y", "M", "6", "1")
    YUV444M = _fourcc("Y", "M", "2", "4")
    YVU444M = _fourcc("Y", "M", "4", "2")
    SBGGR8 = _fourcc("B", "A", "8", "1")
    SGBRG8 = _fourcc("G", "B", "R", "G")
    SGRBG8 = _fourcc("G", "R", "B", "G")
    SRGGB8 = _fourcc("R", "G", "G", "B")
    SBGGR10 = _fourcc("B", "G", "1", "0")
    SGBRG10 = _fourcc("G", "B", "1", "0")
    SGRBG10 = _fourcc("B", "A", "1", "0")
    SRGGB10 = _fourcc("R", "G", "1", "0")
    SBGGR10P = _fourcc("p", "B", "A", "A")
    SGBRG10P = _fourcc("p", "G", "A", "A")
    SGRBG10P = _fourcc("p", "g", "A", "A")
    SRGGB10P = _fourcc("p", "R", "A", "A")
    SBGGR10ALAW8 = _fourcc("a", "B", "A", "8")
    SGBRG10ALAW8 = _fourcc("a", "G", "A", "8")
    SGRBG10ALAW8 = _fourcc("a", "g", "A", "8")
    SRGGB10ALAW8 = _fourcc("a", "R", "A", "8")
    SBGGR10DPCM8 = _fourcc("b", "B", "A", "8")
    SGBRG10DPCM8 = _fourcc("b", "G", "A", "8")
    SGRBG10DPCM8 = _fourcc("B", "D", "1", "0")
    SRGGB10DPCM8 = _fourcc("b", "R", "A", "8")
    SBGGR12 = _fourcc("B", "G", "1", "2")
    SGBRG12 = _fourcc("G", "B", "1", "2")
    SGRBG12 = _fourcc("B", "A", "1", "2")
    SRGGB12 = _fourcc("R", "G", "1", "2")
    SBGGR16 = _fourcc("B", "Y", "R", "2")
    MJPEG = _fourcc("M", "J", "P", "G")
    JPEG = _fourcc("J", "P", "E", "G")
    DV = _fourcc("d", "v", "s", "d")
    MPEG = _fourcc("M", "P", "E", "G")
    H264 = _fourcc("H", "2", "6", "4")
    H264_NO_SC = _fourcc("A", "V", "C", "1")
    H264_MVC = _fourcc("M", "2", "6", "4")
    H263 = _fourcc("H", "2", "6", "3")
    MPEG1 = _fourcc("M", "P", "G", "1")
    MPEG2 = _fourcc("M", "P", "G", "2")
    MPEG4 = _fourcc("M", "P", "G", "4")
    XVID = _fourcc("X", "V", "I", "D")
    VC1_ANNEX_G = _fourcc("V", "C", "1", "G")
    VC1_ANNEX_L = _fourcc("V", "C", "1", "L")
    VP8 = _fourcc("V", "P", "8", "0")
    CPIA1 = _fourcc("C", "P", "I", "A")
    WNVA = _fourcc("W", "N", "V", "A")
    SN9C10X = _fourcc("S", "9", "1", "0")
    SN9C20X_I420 = _fourcc("S", "9", "2", "0")
    PWC1 = _fourcc("P", "W", "C", "1")
    PWC2 = _fourcc("P", "W", "C", "2")
    ET61X251 = _fourcc("E", "6", "2", "5")
    SPCA501 = _fourcc("S", "5", "0", "1")
    SPCA505 = _fourcc("S", "5", "0", "5")
    SPCA508 = _fourcc("S", "5", "0", "8")
    SPCA561 = _fourcc("S", "5", "6", "1")
    PAC207 = _fourcc("P", "2", "0", "7")
    MR97310A = _fourcc("M", "3", "1", "0")
    JL2005BCD = _fourcc("J", "L", "2", "0")
    SN9C2028 = _fourcc("S", "O", "N", "X")
    SQ905C = _fourcc("9", "0", "5", "C")
    PJPG = _fourcc("P", "J", "P", "G")
    OV511 = _fourcc("O", "5", "1", "1")
    OV518 = _fourcc("O", "5", "1", "8")
    STV0680 = _fourcc("S", "6", "8", "0")
    TM6000 = _fourcc("T", "M", "6", "0")
    CIT_YYVYUY = _fourcc("C", "I", "T", "V")
    KONICA420 = _fourcc("K", "O", "N", "I")
    JPGL = _fourcc("J", "P", "G", "L")
    SE401 = _fourcc("S", "4", "0", "1")
    S5C_UYVY_JPG = _fourcc("S", "5", "C", "I")
    Y8I = _fourcc("Y", "8", "I", " ")
    Y12I = _fourcc("Y", "1", "2", "I")
    Z16 = _fourcc("Z", "1", "6", " ")


class V4L2_BUF_TYPE(enum.IntEnum):
    VIDEO_CAPTURE = 1
    VIDEO_OUTPUT = 2
    VIDEO_OVERLAY = 3
    VBI_CAPTURE = 4
    VBI_OUTPUT = 5
    SLICED_VBI_CAPTURE = 6
    SLICED_VBI_OUTPUT = 7
    VIDEO_OUTPUT_OVERLAY = 8
    VIDEO_CAPTURE_MPLANE = 9
    VIDEO_OUTPUT_MPLANE = 10
    SDR_CAPTURE = 11
    SDR_OUTPUT = 12
    PRIVATE = 0x80


class V4L2_FRMSIZE_TYPE(enum.IntEnum):
    DISCRETE = 1
    CONTINUOUS = 2
    STEPWISE = 3


class V4L2_FRMIVAL_TYPE(enum.IntEnum):
    DISCRETE = 1
    CONTINUOUS = 2
    STEPWISE = 3


class V4L2_FIELD(enum.IntEnum):
    ANY = 0
    NONE = 1
    TOP = 2
    BOTTOM = 3
    INTERLACED = 4
    SEQ_TB = 5
    SEQ_BT = 6
    ALTERNATE = 7
    INTERLACED_TB = 8
    INTERLACED_BT = 9


V4L2_MODE_HIGHQUALITY = 0x0001
V4L2_CAP_TIMEPERFRAME = 0x1000


class V4L2_MEMORY(enum.IntEnum):
    MMAP = 1
    USERPTR = 2
    OVERLAY = 3
    DMABUF = 4


VideoPort = enum.Enum("VideoPort", "CSI USB")


class VideoConfig(object):
    def __init__(self, width=640, height=480, pixel_format=V4L2_PIX_FMT.RGB24, framerate=30):
        self.pixel_format = pixel_format
        self.width = width
        self.height = height
        self.interval = fract()
        self.interval.numerator = 1
        self.interval.denominator = framerate


class Video(object):
    def __init__(self, device="/dev/video0", blocking=False):
        self.device = device
        flags = os.O_RDWR
        if not blocking:
            flags |= os.O_NONBLOCK
        self.device_fd = os.open(self.device, flags)
        self.converter = _v4lconvert.create(self.device_fd)

    def close(self):
        os.close(self.device_fd)

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, trace):
        self.close()

    def _ioctl(self, request, arg):
        while True:
            result = _v4l2.ioctl(self.device_fd, request, arg)
            e = get_errno()
            if not (((-1 == result) and ((e == errno.EINTR) or (e == errno.EAGAIN)))):
                break
        return result

    def query_capability(self):
        cap = capability()
        result = self._ioctl(_VIDIOC.QUERYCAP, byref(cap))
        if not (cap.capabilities & _V4L2_CAP_VIDEO_CAPTURE):
            raise RuntimeError("The device doesn't support the single-planar API through the Video Capture interface.")
        if not (cap.capabilities & _V4L2_CAP_STREAMING):
            raise RuntimeError("The device doesn't support the streaming I/O method.")
        driver = "".join(map(chr, itertools.takewhile(lambda x: x > 0, cap.driver)))
        if driver == "bm2835 mmal":
            return VideoPort.CSI
        elif driver[: len("uvcvideo")] == "uvcvideo":
            return VideoPort.USB
        else:
            raise RuntimeError("unknown driver '{}'".format(driver))

    def lookup_config(self, width, height, framerate, pixel_format, expected_format):

        results = []

        candidate = VideoConfig()

        def infinite_range():
            i = 0
            while True:
                yield i
                i += 1

        for i in infinite_range():

            fmt = fmtdesc()
            fmt.index = i
            fmt.type = V4L2_BUF_TYPE.VIDEO_CAPTURE

            result = _v4l2.ioctl(self.device_fd, _VIDIOC.ENUM_FMT, byref(fmt))
            if result != 0 and get_errno() == errno.EINVAL:
                break
            if result != 0:
                raise RuntimeError(errno.errorcode[get_errno()])

            if not fmt.pixelformat == pixel_format:
                continue

            candidate.pixel_format = fmt.pixelformat

            for j in infinite_range():
                frmsize = frmsizeenum()
                frmsize.index = j
                frmsize.pixel_format = fmt.pixelformat

                result = _v4l2.ioctl(self.device_fd, _VIDIOC.ENUM_FRAMESIZES, byref(frmsize))
                if result != 0 and get_errno() == errno.EINVAL:
                    break
                if result != 0:
                    raise RuntimeError(errno.errorcode[get_errno()])

                if frmsize.type == V4L2_FRMSIZE_TYPE.DISCRETE:
                    if width <= frmsize.discrete.width and height <= frmsize.discrete.height:
                        candidate.width = frmsize.discrete.width
                        candidate.height = frmsize.discrete.height
                    else:
                        continue
                elif frmsize.type == V4L2_FRMSIZE_TYPE.CONTINUOUS:
                    if (
                        frmsize.stepwise.min_width <= width
                        and width <= frmsize.stepwise.max_width
                        and frmsize.stepwise.min_height <= height
                        and height <= frmsize.stepwise.max_height
                    ):
                        candidate.width = width
                        candidate.height = height
                    else:
                        continue
                elif frmsize.type == V4L2_FRMSIZE_TYPE.STEPWISE:
                    if (
                        frmsize.stepwise.min_width <= width
                        and width <= frmsize.stepwise.max_width
                        and frmsize.stepwise.min_height <= height
                        and height <= frmsize.stepwise.max_height
                    ):
                        candidate.width = (
                            width - frmsize.stepwise.min_width + frmsize.stepwise.step_width - 1
                        ) // frmsize.stepwise.step_width * frmsize.stepwise.step_width + frmsize.stepwise.min_width
                        candidate.height = (
                            height - frmsize.stepwise.min_height + frmsize.stepwise.step_height - 1
                        ) // frmsize.stepwise.step_height * frmsize.stepwise.step_height + frmsize.stepwise.min_height
                    else:
                        continue
                else:
                    continue

                for k in infinite_range():
                    frmival = frmivalenum()
                    frmival.index = k
                    frmival.pixel_format = candidate.pixel_format
                    frmival.width = candidate.width
                    frmival.height = candidate.height

                    result = _v4l2.ioctl(self.device_fd, _VIDIOC.ENUM_FRAMEINTERVALS, byref(frmival))
                    if result != 0 and get_errno() == errno.EINVAL:
                        break
                    if result != 0:
                        raise RuntimeError(errno.errorcode[get_errno()])

                    if frmival.type == V4L2_FRMIVAL_TYPE.DISCRETE:
                        rate = frmival.discrete.denominator * 1.0 / frmival.discrete.numerator
                        if framerate <= rate:
                            candidate.interval = frmival.discrete
                        else:
                            continue
                    elif frmival.type == V4L2_FRMIVAL_TYPE.CONTINUOUS:
                        min_rate = frmival.stepwise.max.denominator * 1.0 / frmival.stepwise.max.numerator
                        max_rate = frmival.stepwise.min.denominator * 1.0 / frmival.stepwise.min.numerator
                        if min_rate <= framerate and framerate <= max_rate:
                            candidate.interval.numerator = 1
                            candidate.interval.denominator = framerate
                        else:
                            continue
                    elif frmival.type == V4L2_FRMIVAL_TYPE.STEPWISE:
                        min_rate = frmival.stepwise.max.denominator * 1.0 / frmival.stepwise.max.numerator
                        max_rate = frmival.stepwise.min.denominator * 1.0 / frmival.stepwise.min.numerator
                        step_rate = frmival.stepwise.step.denominator * 1.0 / frmival.stepwise.step.numerator
                        if min_rate <= framerate and framerate <= max_rate:
                            s = 0
                            while True:
                                mn = frmival.stepwise.max.numerator
                                md = frmival.stepwise.max.denominator
                                sn = frmival.stepwise.step.numerator
                                sd = frmival.stepwise.step.denominator
                                n = mn * sd - s * sn * md
                                d = md * sd
                                rate = d * 1.0 / n
                                if framerate <= rate:
                                    candidate.interval.numerator = n
                                    candidate.interval.denominator = d
                                    break
                        else:
                            continue
                    else:
                        continue

                    if expected_format == pixel_format:
                        results.append(candidate)
                    else:
                        if self.try_convert(candidate, candidate.width, candidate.height, expected_format) is not None:
                            results.append(candidate)

                    old_candidate = candidate
                    candidate = VideoConfig()
                    candidate.pixel_format = old_candidate.pixel_format
                    candidate.width = old_candidate.width
                    candidate.height = old_candidate.height

        return results

    def try_convert(self, conf, expected_width, expected_height, expected_format):

        fmt = format()
        fmt.type = V4L2_BUF_TYPE.VIDEO_CAPTURE
        fmt.fmt.pix.width = conf.width
        fmt.fmt.pix.height = conf.height
        fmt.fmt.pix.pixelformat = conf.pixel_format
        fmt.fmt.pix.field = V4L2_FIELD.INTERLACED

        expected_fmt = format()
        expected_fmt.type = V4L2_BUF_TYPE.VIDEO_CAPTURE
        expected_fmt.fmt.pix.width = expected_width
        expected_fmt.fmt.pix.height = expected_height
        expected_fmt.fmt.pix.pixelformat = expected_format
        expected_fmt.fmt.pix.field = V4L2_FIELD.INTERLACED

        result = _v4lconvert.try_format(self.converter, byref(expected_fmt), byref(fmt))
        if -1 == result:
            raise RuntimeError("incompatible format")

        before = (expected_width, expected_height, expected_format)
        after = (expected_fmt.fmt.pix.width, expected_fmt.fmt.pix.height, expected_fmt.fmt.pix.pixelformat)

        if before == after:
            return (fmt, expected_fmt)
        else:
            return None

    def set_format(self, conf, expected_width=None, expected_height=None, expected_format=None):

        if expected_width is None:
            expected_width = conf.width
        if expected_height is None:
            expected_height = conf.height
        if expected_format is None:
            expected_format = conf.pixel_format

        fmts = self.try_convert(conf, expected_width, expected_height, expected_format)
        if fmts is None:
            fmts = self.try_convert(conf, conf.width, conf.height, expected_format)
            if fmts is None:
                raise RuntimeError("incompatible format")

        (self.fmt, self.expected_fmt) = fmts
        result = self._ioctl(_VIDIOC.S_FMT, byref(self.fmt))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_S_FMT)")

        return (self.expected_fmt.fmt.pix.width, self.expected_fmt.fmt.pix.height, self.expected_fmt.fmt.pix.pixelformat)

    def set_framerate(self, conf):

        parm = streamparm()
        parm.type = V4L2_BUF_TYPE.VIDEO_CAPTURE
        parm.parm.capture.timeperframe = conf.interval
        parm.parm.capture.capturemode = V4L2_MODE_HIGHQUALITY

        result = self._ioctl(_VIDIOC.S_PARM, byref(parm))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_S_PARM)")

        return True

    def set_rotation(self, rotation):
        """
        Rotate video if it supported.

        Args:
            rotation (int): video rotation (must be multiples of 90)

        Returns:
            boolean: result
        """

        assert rotation % 90 == 0, "rotation must be multiples of 90"
        rot = (rotation // 90) % 4 * 90  # [0, 90, 180, 270]

        qctrl = queryctrl()
        qctrl.id = V4L2_CID.ROTATE
        result = self._ioctl(_VIDIOC.QUERYCTRL, byref(qctrl))
        if -1 == result:
            return False

        ctrl = control()
        ctrl.id = V4L2_CID.ROTATE
        ctrl.value = rot

        result = self._ioctl(_VIDIOC.S_CTRL, byref(ctrl))
        if -1 == result:
            return False

        return True

    def set_horizontal_flip(self, flip):
        """
        Flip video (horizontal) if it supported.

        Args:
            flip (boolean): enable flip

        Returns:
            boolean: result
        """

        qctrl = queryctrl()
        qctrl.id = V4L2_CID.HFLIP
        result = self._ioctl(_VIDIOC.QUERYCTRL, byref(qctrl))
        if -1 == result:
            return False
        if qctrl.flags & V4L2_CTRL_FLAG_DISABLED:
            return False

        ctrl = control()
        ctrl.id = V4L2_CID.HFLIP
        ctrl.value = flip

        result = self._ioctl(_VIDIOC.S_CTRL, byref(ctrl))
        if -1 == result:
            return False
        expected = ctrl.value
        result = self._ioctl(_VIDIOC.G_CTRL, byref(ctrl))
        if -1 == result:
            return False
        if expected != ctrl.value:
            return False

        return True

    def set_vertical_flip(self, flip):
        """
        Flip video (vertical) if it supported.

        Args:
            flip (boolean): enable flip

        Returns:
            boolean: result
        """

        qctrl = queryctrl()
        qctrl.id = V4L2_CID.VFLIP
        result = self._ioctl(_VIDIOC.QUERYCTRL, byref(qctrl))
        if -1 == result:
            return False
        if qctrl.flags & V4L2_CTRL_FLAG_DISABLED:
            return False

        ctrl = control()
        ctrl.id = V4L2_CID.VFLIP
        ctrl.value = flip

        result = self._ioctl(_VIDIOC.S_CTRL, byref(ctrl))
        if -1 == result:
            return False
        expected = ctrl.value
        result = self._ioctl(_VIDIOC.G_CTRL, byref(ctrl))
        if -1 == result:
            return False
        if expected != ctrl.value:
            return False

        return True

    def set_exposure_time(self, ms=None):
        """
        Set exposure time.

        Args:
            ms (int or None): exposure time [msec] (None means auto)

        Returns:
            boolean: result
        """

        if ms is None:
            ctrl = control()
            ctrl.id = V4L2_CID.EXPOSURE_AUTO
            ctrl.value = V4L2_EXPOSURE.AUTO
            result = self._ioctl(_VIDIOC.S_CTRL, byref(ctrl))
            if -1 == result:
                return False
            expected = ctrl.value
            result = self._ioctl(_VIDIOC.G_CTRL, byref(ctrl))
            if -1 == result:
                return False
            if expected != ctrl.value:
                return False
        else:
            ctrl = control()
            ctrl.id = V4L2_CID.EXPOSURE_AUTO
            ctrl.value = V4L2_EXPOSURE.MANUAL
            result = self._ioctl(_VIDIOC.S_CTRL, byref(ctrl))
            if -1 == result:
                return False
            expected = ctrl.value
            result = self._ioctl(_VIDIOC.G_CTRL, byref(ctrl))
            if -1 == result:
                return False
            if expected != ctrl.value:
                return False

            ctrl.id = V4L2_CID.EXPOSURE_ABSOLUTE
            ctrl.value = int(10 * ms)  # [100us]
            result = self._ioctl(_VIDIOC.S_CTRL, byref(ctrl))
            if -1 == result:
                return False
            expected = ctrl.value
            result = self._ioctl(_VIDIOC.G_CTRL, byref(ctrl))
            if -1 == result:
                return False
            if expected != ctrl.value:
                return False

        return True

    def request_buffers(self, n):

        req = requestbuffers()
        req.count = n
        req.type = V4L2_BUF_TYPE.VIDEO_CAPTURE
        req.memory = V4L2_MEMORY.MMAP

        result = self._ioctl(_VIDIOC.REQBUFS, byref(req))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_REQBUFS): {}".format(errno.errorcode[get_errno()]))

        return [VideoBuffer._from_query(self, i) for i in range(n)]

    def queue_buffer(self, video_buf):

        result = self._ioctl(_VIDIOC.QBUF, byref(video_buf.buf))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_QBUF): {}".format(errno.errorcode[get_errno()]))

        return True

    def start_streaming(self):

        cap = c_int(V4L2_BUF_TYPE.VIDEO_CAPTURE)
        result = self._ioctl(_VIDIOC.STREAMON, byref(cap))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_STREAMON): {}".format(errno.errorcode[get_errno()]))

        return VideoStream(self)

    def stop_streaming(self):

        cap = c_int(V4L2_BUF_TYPE.VIDEO_CAPTURE)
        result = self._ioctl(_VIDIOC.STREAMOFF, byref(cap))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_STREAMON): {}".format(errno.errorcode[get_errno()]))

        return True

    def dequeue_buffer(self, timeout=1):
        class FDWrapper:
            def __init__(self, fd):
                self.fd = fd

            def fileno(self):
                return self.fd

        rlist, _, _ = select.select([FDWrapper(self.device_fd)], [], [], timeout)
        if len(rlist) == 0:
            raise RuntimeError("Capture timeout")

        buf = buffer()
        buf.type = V4L2_BUF_TYPE.VIDEO_CAPTURE
        buf.memory = V4L2_MEMORY.MMAP
        result = self._ioctl(_VIDIOC.DQBUF, byref(buf))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_DQBUF): {}".format(errno.errorcode[get_errno()]))

        return VideoBuffer(self, buf)

    def requeue_buffer(self, video_buf):

        result = self._ioctl(_VIDIOC.QBUF, byref(video_buf.buf))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_QBUF): {}".format(errno.errorcode[get_errno()]))


class VideoStream(object):
    def __init__(self, video):
        self.video = video

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, trace):
        self.video.stop_streaming()

    def capture(self, timeout=1, in_expected_format=True):

        buf = self.video.dequeue_buffer(timeout=timeout)
        mapped_buf = buf.get_mapped_buffer()

        dst = bytes(self.video.expected_fmt.fmt.pix.sizeimage)
        if in_expected_format:
            _v4lconvert.convert(
                self.video.converter,
                byref(self.video.fmt),
                byref(self.video.expected_fmt),
                mapped_buf,
                self.video.fmt.fmt.pix.sizeimage,
                cast(dst, POINTER(c_uint8)),
                self.video.expected_fmt.fmt.pix.sizeimage,
            )
        else:
            stream = io.BytesIO(dst)
            stream.write(mapped_buf.contents)

        buf.unmap_buffer()
        self.video.requeue_buffer(buf)

        return dst


class VideoBuffer(object):
    @classmethod
    def _from_query(cls, video, index):

        buf = buffer()
        buf.type = V4L2_BUF_TYPE.VIDEO_CAPTURE
        buf.memory = V4L2_MEMORY.MMAP
        buf.index = index

        set_errno(0)
        result = video._ioctl(_VIDIOC.QUERYBUF, byref(buf))
        if -1 == result:
            raise RuntimeError("ioctl(VIDIOC_QYERYBUF): {}".format(errno.errorcode[get_errno()]))

        return cls(video, buf)

    def __init__(self, video, buf):
        self.video = video
        self.buf = buf
        self.mapped_buf = None

    def get_mapped_buffer(self):
        if self.mapped_buf is not None:
            return self.mapped_buf
        result = _v4l2.mmap(
            None,
            self.buf.length,
            mmap.PROT_READ | mmap.PROT_WRITE,
            mmap.MAP_SHARED,
            self.video.device_fd,
            c_longlong(self.buf.m.offset),
        )
        if result == -1:
            raise RuntimeError("mmap failed: {}".format(errno.errorcode[get_errno()]))
        self.mapped_buf = cast(result, POINTER(ARRAY(c_uint8, self.buf.length)))
        return self.mapped_buf

    def unmap_buffer(self):
        if self.mapped_buf is None:
            return
        result = _v4l2.munmap(self.mapped_buf, self.buf.length)
        if result == -1:
            raise RuntimeError("munmap failed: {}".format(errno.errorcode[get_errno()]))
        self.mapped_buf = None


# if __name__ == '__main__':

#     from PIL import Image
#     import traceback

#     with Video('/dev/video1') as video:
#         print("video.query_capability():",video.query_capability())
#         candidates = video.lookup_config(640, 480, 30, V4L2_PIX_FMT.RGB24) + video.lookup_config(640, 480, 30, V4L2_PIX_FMT.YUYV)
#         for i, config in enumerate(candidates):
#             print("video.lookup_config index:", i,
#                   V4L2_PIX_FMT(config.pixel_format), config.width, config.height,
#                   config.interval.denominator / config.interval.numerator)
#         config = candidates[0]
#         print("video.set_format(config):",video.set_format(config, 320, 240, V4L2_PIX_FMT.RGB24))
#         print("video.set_framerate(config):",video.set_framerate(config))
#         print("video.set_rotation(90):", video.set_rotation(90))
#         num_of_buffers = 2
#         buffers = video.request_buffers(num_of_buffers)
#         print("video.request_buffers({}):".format(num_of_buffers), buffers)
#         for buf in buffers:
#             print("video.queue_buffer({}):".format(buf), video.queue_buffer(buf))
#         with video.start_streaming() as stream:
#             try:
#                 for i in range(5):
#                     dat = stream.capture()
#                     img = Image.fromarray(np.frombuffer(dat, dtype=np.uint8).reshape(240,320,3))
#                     img.save('{:03d}.png'.format(i))
#             except:
#                 print(traceback.format_exc())
