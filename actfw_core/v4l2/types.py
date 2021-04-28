# flake8: noqa

from ctypes import *


class capability(Structure):
    _fields_ = [
        ("driver", c_ubyte * 16),
        ("card", c_ubyte * 32),
        ("bus_info", c_ubyte * 32),
        ("version", c_uint),
        ("capabilities", c_uint),
        ("device_caps", c_uint),
        ("reserved", c_uint * 3),
    ]


class fmtdesc(Structure):
    _fields_ = [
        ("index", c_uint),
        ("type", c_uint),
        ("flags", c_uint),
        ("description", c_ubyte * 32),
        ("pixelformat", c_uint),
        ("reserved", c_uint * 4),
    ]


class frmsize_discrete(Structure):
    _fields_ = [
        ("width", c_uint),
        ("height", c_uint),
    ]


class frmsize_stepwise(Structure):
    _fields_ = [
        ("min_width", c_uint),
        ("max_width", c_uint),
        ("step_width", c_uint),
        ("min_height", c_uint),
        ("max_height", c_uint),
        ("step_height", c_uint),
    ]


class _frmsize_for_frmsizeenum(Union):
    _fields_ = [
        ("discrete", frmsize_discrete),
        ("stepwise", frmsize_stepwise),
    ]


class frmsizeenum(Structure):
    _anonymous_ = ("_frmsize",)
    _fields_ = [
        ("index", c_uint),
        ("pixel_format", c_uint),
        ("type", c_uint),
        ("_frmsize", _frmsize_for_frmsizeenum),
        ("reserved", c_uint * 2),
    ]


class fract(Structure):
    _fields_ = [
        ("numerator", c_uint),
        ("denominator", c_uint),
    ]


class frmival_stepwise(Structure):
    _fields_ = [
        ("min", fract),
        ("max", fract),
        ("step", fract),
    ]


class _frmival_for_frmivalenum(Union):
    _fields_ = [
        ("discrete", fract),
        ("stepwise", frmival_stepwise),
    ]


class frmivalenum(Structure):
    _anonymous_ = ("_frmival",)
    _fields_ = [
        ("index", c_uint),
        ("pixel_format", c_uint),
        ("width", c_uint),
        ("height", c_uint),
        ("type", c_uint),
        ("_frmival", _frmival_for_frmivalenum),
        ("reserved", c_uint * 2),
    ]


class pix_format(Structure):
    _fields_ = [
        ("width", c_uint),
        ("height", c_uint),
        ("pixelformat", c_uint),
        ("field", c_uint),
        ("bytesperline", c_uint),
        ("sizeimage", c_uint),
        ("colorspace", c_uint),
        ("priv", c_uint),
        ("flags", c_uint),
        ("ycbcr_enc", c_uint),
        ("quantization", c_uint),
        ("xfer_func", c_uint),
    ]


class plane_pix_format(Structure):
    _fields_ = [
        ("sizeimage", c_uint),
        ("bytesperline", c_uint),
        ("reserved", c_ushort * 6),
    ]


class pix_format_mplane(Structure):
    _fields_ = [
        ("width", c_uint),
        ("height", c_uint),
        ("pixelformat", c_uint),
        ("field", c_uint),
        ("colorspace", c_uint),
        ("plane_fmt", plane_pix_format * 8),  # VIDEO_MAX_PLANES
        ("num_planes", c_ubyte),
        ("flags", c_ubyte),
        ("ycbcr_enc", c_ubyte),
        ("quantization", c_ubyte),
        ("xfer_func", c_ubyte),
        ("reserved", c_ubyte * 7),
    ]


class rect(Structure):
    _fields_ = [
        ("left", c_int),
        ("top", c_int),
        ("width", c_uint),
        ("height", c_uint),
    ]


class clip(Structure):
    pass


clip._fields_ = [
    ("c", rect),
    ("next", POINTER(clip)),
]


class window(Structure):
    _fields_ = [
        ("w", rect),
        ("field", c_uint),
        ("chromakey", c_uint),
        ("clips", POINTER(clip)),
        ("clipcount", c_uint),
        ("bitmap", c_void_p),
        ("global_alpha", c_ubyte),
    ]


class vbi_format(Structure):
    _fields_ = [
        ("sampling_rate", c_uint),
        ("offset", c_uint),
        ("samples_per_line", c_uint),
        ("sample_format", c_uint),
        ("start", c_int * 2),
        ("count", c_uint * 2),
        ("flags", c_uint),
        ("reserved", c_uint * 2),
    ]


class sliced_vbi_format(Structure):
    _fields_ = [
        ("service_lines", 2 * (24 * c_ushort)),
        ("io_size", c_uint),
        ("reserved", c_uint * 2),
    ]


class sdr_format(Structure):
    _fields_ = [
        ("pixelformat", c_uint),
        ("buffersize", c_uint),
        ("reserved", c_ubyte * 24),
    ]


class _fmt_for_format(Union):
    _fields_ = [
        ("pix", pix_format),
        ("pix_mp", pix_format_mplane),
        ("win", window),
        ("vbi", vbi_format),
        ("sliced", sliced_vbi_format),
        ("sdr", sdr_format),
        ("raw_data", c_ubyte * 200),
    ]


class format(Structure):
    _fields_ = [
        ("type", c_uint),
        ("fmt", _fmt_for_format),
    ]


class captureparm(Structure):
    _fields_ = [
        ("capability", c_uint),
        ("capturemode", c_uint),
        ("timeperframe", fract),
        ("extendedmode", c_uint),
        ("readbufferbs", c_uint),
        ("reserved", c_uint * 4),
    ]


class outputparm(Structure):
    _fields_ = [
        ("capability", c_uint),
        ("outputmode", c_uint),
        ("timeperframe", fract),
        ("extendedmode", c_uint),
        ("writebuffers", c_uint),
        ("reserved", c_uint * 4),
    ]


class _parm_for_streamparm(Union):
    _fields_ = [
        ("capture", captureparm),
        ("output", outputparm),
        ("raw_data", c_ubyte * 200),
    ]


class streamparm(Structure):
    _fields_ = [
        ("type", c_uint),
        ("parm", _parm_for_streamparm),
    ]


class control(Structure):
    _fields_ = [
        ("id", c_uint),
        ("value", c_int),
    ]


class queryctrl(Structure):
    _fields_ = [
        ("id", c_uint),
        ("type", c_uint),
        ("name", c_ubyte * 32),
        ("minimum", c_int),
        ("maximum", c_int),
        ("step", c_int),
        ("default_value", c_int),
        ("flags", c_uint),
        ("reserved", c_uint * 2),
    ]


class requestbuffers(Structure):
    _fields_ = [
        ("count", c_uint),
        ("type", c_uint),
        ("memory", c_uint),
        ("reserved", c_uint * 2),
    ]


class timeval(Structure):
    _fields_ = [
        ("sec", c_long),
        ("usec", c_long),
    ]


class timecode(Structure):
    _fields_ = [
        ("type", c_uint),
        ("flags", c_uint),
        ("frames", c_ubyte),
        ("seconds", c_ubyte),
        ("minutes", c_ubyte),
        ("hours", c_ubyte),
        ("userbits", c_ubyte * 4),
    ]


class _m_for_plane(Union):
    _fields_ = [
        ("mem_offset", c_uint),
        ("userptr", c_ulong),
        ("fd", c_int),
    ]


class plane(Structure):
    _fields_ = [
        ("bytesused", c_uint),
        ("length", c_uint),
        ("m", _m_for_plane),
        ("data_offset", c_uint),
        ("reserved", c_uint * 11),
    ]


class _m_for_buffer(Union):
    _fields_ = [
        ("offset", c_uint),
        ("userptr", c_ulong),
        ("planes", POINTER(plane)),
        ("fd", c_int),
    ]


class buffer(Structure):
    _fields_ = [
        ("index", c_uint),
        ("type", c_uint),
        ("bytesused", c_uint),
        ("flags", c_uint),
        ("field", c_uint),
        ("timestamp", timeval),
        ("timecode", timecode),
        ("sequence", c_uint),
        ("memory", c_uint),
        ("m", _m_for_buffer),
        ("length", c_uint),
        ("reserved2", c_uint),
        ("reserved", c_uint),
    ]
