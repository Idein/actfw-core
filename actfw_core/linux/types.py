from ctypes import *


class dma_heap_allocation_data(Structure):
    _fields_ = [("len", c_uint64), ("fd", c_uint32), ("fd_flags", c_uint32), ("heap_flags", c_uint64)]
