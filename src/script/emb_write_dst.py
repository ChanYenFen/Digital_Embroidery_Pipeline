"""
emb_write_dst.py
Final stage of the embroidery pipeline: Converts structured data to .DST format.
Uses the pyembroidery library to handle stitch commands and file export.
"""
__author__ = "Yen-Fen Chan"
__date__ = "2024.05.31"
__update__ = "2026.03.16"

import os
import math
import pyembroidery

from misc import unload_modules
unload_modules("emb_constants")
from emb_constants import*

# =========================================================
# Parameters
# =========================================================
export = export if 'export' in locals() else False             # type: ignore
in_dict = in_dict if 'in_dict' in locals() else None           # type: ignore
folder_path = folder_path if 'folder_path' in locals() else "" # type: ignore
name = name if 'name' in locals() else "output"                # type: ignore

if export and in_dict:
    # 1. Initialize pyembroidery pattern
    pattern = pyembroidery.EmbPattern()
    
    # Extract lists from the input dictionary
    path_indices = in_dict["PATH_INDEX"]
    xs = in_dict["X"]
    ys = in_dict["Y"]
    colors = in_dict["COLOR"]
    types = in_dict["TYPE"]
    
    total_pts = len(xs)

    # 2. Core Conversion Logic
    for i in range(total_pts):
        cur_x = int(xs[i] * 10)
        cur_y = int(ys[i] * 10)
        
        cur_idx = path_indices[i]
        cur_type = types[i]
        cur_color = colors[i]
        
        is_first_in_seg = (i == 0) or (path_indices[i-1] != cur_idx)
        is_last_in_seg = (i == total_pts - 1) or (path_indices[i+1] != cur_idx)

        # ==========================================================
        # 1. PRIMARY MOVEMENT (Old Block B)
        # We handle all physical spatial movements here first.
        # ==========================================================
        command = "STITCH" if cur_type in THREAD_STITCH_TYPES else "JUMP"
        
        # Long Stitch Subdivision (Only for STITCH commands within a segment)
        if not is_first_in_seg and command == "STITCH":
            prev_x = int(xs[i-1] * 10)
            prev_y = int(ys[i-1] * 10)
            dist = math.sqrt((cur_x - prev_x)**2 + (cur_y - prev_y)**2)
            
            if dist > JUMP_THRESHOLD:
                steps = int(math.ceil(dist / float(JUMP_THRESHOLD)))
                for k in range(1, steps):
                    inter_x = int(prev_x + (cur_x - prev_x) * k / steps)
                    inter_y = int(prev_y + (cur_y - prev_y) * k / steps)
                    pattern.add_stitch_absolute(pyembroidery.JUMP, inter_x, inter_y)

        # Write the actual movement to reach the current point
        py_cmd = pyembroidery.STITCH if command == "STITCH" else pyembroidery.JUMP
        pattern.add_stitch_absolute(py_cmd, cur_x, cur_y)

        # ==========================================================
        # 2. START-OF-SEGMENT SETUP (Optimized Block A)
        # The needle has now arrived. If it's a cable, pause the machine.
        # ==========================================================
        if is_first_in_seg and cur_type in CABLE_STOP_TYPES:
            prev_type = types[i-1] if i > 0 else None
            
            # Check if we transitioned from standard thread (EMB/ETS) 
            # or if this is the very first line of the whole file.
            if prev_type not in CABLE_STOP_TYPES:
                # Needle is in position. Inject double CC for operator to load the cable.
                pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, cur_x, cur_y)
                pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, cur_x, cur_y)

        # ==========================================================
        # 3. END-OF-SEGMENT COMMANDS (Optimized Block C)
        # Decide how to exit this line.
        # ==========================================================
        if is_last_in_seg:
            is_end_of_pattern = (i == total_pts - 1)
            next_type = types[i+1] if not is_end_of_pattern else None
            next_color = colors[i+1] if not is_end_of_pattern else None

            # Hybrid Type (CTS): Needs trimming and cable pause
            if cur_type in THREAD_STITCH_TYPES and cur_type in CABLE_STOP_TYPES:
                pattern.add_stitch_absolute(pyembroidery.TRIM, cur_x, cur_y)
                pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, cur_x, cur_y)
                pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, cur_x, cur_y)

            # Pure Cable Type (WIN): Only needs cable pause
            elif cur_type in CABLE_STOP_TYPES:
                pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, cur_x, cur_y)
                pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, cur_x, cur_y)

            # Pure Thread Type (EMB, ETS): Needs to check next segment
            elif cur_type in THREAD_STITCH_TYPES and not is_end_of_pattern:
                if next_type in CABLE_STOP_TYPES:
                    pattern.add_stitch_absolute(pyembroidery.TRIM, cur_x, cur_y)
                elif next_color != cur_color:
                    pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, cur_x, cur_y)
                else:
                    pattern.add_stitch_absolute(pyembroidery.TRIM, cur_x, cur_y)

    # --- E. Final Sequence ---
    # After all points are processed, move to origin and END
    pattern.add_stitch_absolute(pyembroidery.JUMP, 0, 0)
    pattern.add_stitch_absolute(pyembroidery.END, 0, 0)

    # 3. File Export
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    dst_path = os.path.normpath(os.path.join(folder_path, "dst", name + ".dst"))
    csv_path = os.path.normpath(os.path.join(folder_path, "csv", name + ".csv"))

    stop_settings = {
        "contingency": pyembroidery.CONTINGENCY_TIE_OFF_NONE,
        "trim_at" : 9
    }
    # Export DST
    pyembroidery.write(pattern, dst_path, settings=stop_settings)
    
    # Export CSV directly for a clean 1:1 map of the absolute commands
    pyembroidery.write(pattern, csv_path)

    print("Successfully exported: {}".format(dst_path))

else:
    if not export:
        print("Export skipped (export=False).")
    if not in_dict:
        print("Export failed: Input dictionary is missing.")
