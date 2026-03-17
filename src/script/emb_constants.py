__author__ = "fen.chan"
__version__ = "2026.03.16"

# Define all your global sets, lists, and threshold values here
"""
EMB : Emboridery in general
ETS : Embroidery Thread Stitching
CTS : Cable Thread Stitching
WIN : Cable Winding

""" 
THREAD_STITCH_TYPES = {"EMB", "ETS", "CTS"}
CABLE_STOP_TYPES = {"WIN", "CTS"}
JUMP_THRESHOLD = 121
TIE_OFFSET = 10
MIRROR = True