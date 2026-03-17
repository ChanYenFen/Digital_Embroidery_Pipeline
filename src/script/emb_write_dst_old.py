"""
emb_write_dst.py
Final stage of the embroidery pipeline: Converts structured data to .DST format.
Uses the pyembroidery library to handle stitch commands and file export.
"""

import os
import math
import pyembroidery

# =========================================================
# Parameters
# =========================================================
export = export if 'export' in locals() else False          # type: ignore
in_dict = in_dict if 'in_dict' in locals() else None        # type: ignore
folder_path = folder_path if 'folder_path' in locals() else "" # type: ignore
name = name if 'name' in locals() else "output"             # type: ignore

JUMP_THRESHOLD = 121  # 12.1mm (DST unit: 0.1mm)

if export and in_dict:
    # 1. Initialize pyembroidery pattern
    pattern = pyembroidery.EmbPattern()
    
    # Extract lists from the input dictionary
    indices = in_dict["INDEX"]
    xs = in_dict["X"]
    ys = in_dict["Y"]
    colors = in_dict["COLOR"]
    types = in_dict["TYPE"]
    
    total_pts = len(xs)

    # 2. Core Conversion Logic
    for i in range(total_pts):
        # Coordinate Conversion (Rhino mm -> 0.1mm units)
        # Note: DST Y-axis is inverted compared to Rhino; pyembroidery handles 
        # the internal DST conversion during the write process.
        cur_x = int(xs[i] * 10)
        cur_y = int(ys[i] * 10)
        
        cur_idx = indices[i]
        cur_type = types[i]
        cur_color = colors[i]
        
        # Check if this is the last stitch output in the current Segment
        is_last_in_seg = (i == total_pts - 1) or (indices[i+1] != cur_idx)
        
        # --- A. Command Determination Logic ---
        command = "STITCH" # Default command

        print(i)

        if cur_type == "EMB":
            if is_last_in_seg:
                # Check color of the next segment to determine command
                if i < total_pts - 1:
                    next_color = colors[i+1]
                    if next_color != cur_color:
                        command = "COLOR_CHANGE"
                    else:
                        command = "TRIM"
                else:
                    # Final stitch of the entire pattern
                    command = "END"
            else:
                # Avoid redundant stitches on the same coordinate
                if i < total_pts - 1:
                    if xs[i] == xs[i+1] and ys[i] == ys[i+1]:
                        command = "JUMP"

        elif cur_type == "WIN":
            # Winding Mode: Intermediate points are JUMPs. 
            # Final two overlapping points trigger a COLOR_CHANGE.
            if is_last_in_seg:
                command = "COLOR_CHANGE"
            else:
                # Check for the duplicate point before the end (logic from prep script)
                if i < total_pts - 1 and xs[i] == xs[i+1] and ys[i] == ys[i+1] and indices[i+1] == cur_idx:
                    command = "COLOR_CHANGE"
                else:
                    command = "JUMP"
        
        # --- B. Long Stitch Subdivision (Only for STITCH) ---
        if i > 0:
            prev_x = int(xs[i-1] * 10)
            prev_y = int(ys[i-1] * 10)
            dist = math.sqrt((cur_x - prev_x)**2 + (cur_y - prev_y)**2)
            
            # Divide long stitches into JUMPs if they exceed the threshold
            if command == "STITCH" and dist > JUMP_THRESHOLD:
                steps = int(math.ceil(dist / float(JUMP_THRESHOLD)))
                for k in range(1, steps):
                    inter_x = int(prev_x + (cur_x - prev_x) * k / steps)
                    inter_y = int(prev_y + (cur_y - prev_y) * k / steps)
                    pattern.add_stitch_absolute(pyembroidery.JUMP, inter_x, inter_y)

        # --- C. Write pyembroidery Command ---
        cmd_map = {
            "STITCH": pyembroidery.STITCH,
            "JUMP": pyembroidery.JUMP,
            "COLOR_CHANGE": pyembroidery.COLOR_CHANGE,
            "TRIM": pyembroidery.TRIM,
            "END": pyembroidery.END
        }
        
        py_cmd = cmd_map.get(command, pyembroidery.STITCH)
        pattern.add_stitch_absolute(py_cmd, cur_x, cur_y)

    # 3. File Export
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    dst_path = os.path.join(folder_path, name + ".dst")
    csv_path = os.path.join(folder_path, name + ".csv")

    stop_settings = {
        "contingency": pyembroidery.CONTINGENCY_TIE_OFF_NONE,
        "trim_at" : 9
    }

    # Convert .dst to .csv for inspection/debugging if needed
    pyembroidery.write(pattern, dst_path, settings=stop_settings)

    # export_settings = {"trim_at": 9} # same setting as on the machine
    # pyembroidery.convert(dst_path, csv_path, export_settings)
    # writing csv directly is clean
    pyembroidery.write(pattern, csv_path)

    # pyembroidery.write(pattern, full_path)

    print("Successfully exported: {}".format(dst_path))
else:
    if not export:
        print("Export skipped (export=False).")
    if not in_dict:
        print("Export failed: Input dictionary is missing.")