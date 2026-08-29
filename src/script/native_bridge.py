import os
import platform
import ctypes

_DLL = None  # cached handle so the DLL loads only once per session

_LIB_NAMES = {
    "Windows": "curve_sort.dll",
    "Darwin":  "curve_sort.dylib",
    "Linux":   "curve_sort.so",
}


def load_dll():
    """Load curve_sort's native library (once) and declare the sort_curves signature."""
    global _DLL
    if _DLL is not None:
        return _DLL

    here = os.path.dirname(os.path.abspath(__file__))
    lib_name = _LIB_NAMES[platform.system()]
    dll_path = os.path.join(here, "native", lib_name)
    lib = ctypes.CDLL(dll_path)

    # void sort_curves(const double*, int, const double*, int, int, int, int*, int*, double*)
    lib.sort_curves.argtypes = [
        ctypes.POINTER(ctypes.c_double),  # endpoints (6*n)
        ctypes.c_int,                     # n
        ctypes.POINTER(ctypes.c_double),  # start_pt (3)
        ctypes.c_int,                     # use_two_opt
        ctypes.c_int,                     # two_opt_max_passes
        ctypes.c_int,                     # knn_k
        ctypes.c_int,                     # if_flip
        ctypes.POINTER(ctypes.c_int),     # out_order (n)
        ctypes.POINTER(ctypes.c_int),     # out_reversal (n)
        ctypes.POINTER(ctypes.c_double),  # out_travel_points (6*n)
    ]
    lib.sort_curves.restype = None

    _DLL = lib
    return lib
