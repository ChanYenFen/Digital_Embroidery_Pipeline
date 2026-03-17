"""
Python 3 script for Rhino 8 Grasshopper
Geometry Pre-processing for Embroidery & Winding.
Adds caps(both ends of a path), ties(within a path), and jump-stitch logic for .DST export.
"""

__author__ = "Yen-Fen Chan"
__date__ = "2024.10.18"
__update__ = "2026.03.16"

import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th
from itertools import zip_longest
from collections import OrderedDict

from misc import unload_modules
unload_modules("emb_constants")
from emb_constants import*

# =========================================================
# Parameters & Constants
# =========================================================
# JUMP_THRESHOLD = 121   # 12.1mm (unit: 0.1mm)
# TIE_OFFSET = 10        # 1mm  (unit: 0.1mm)

# ACTIVE_STITCH_TYPES = {"EMB", "ETS", "CTS"}
# ACTIVE_JUMP_TYPES = {"WIN"}

jump_vec = rg.Vector3d(0, 0, 50)
origin = rg.Point3d(0, 0, 0)
# =========================================================
# Helper Functions (Geometry Generation)
# =========================================================

def create_cap_pts(start_pt, end_pt, dist):
    """Generates a cap stitch pattern at the start/end of a segment."""
    vec = end_pt - start_pt
    if vec.Length == 0: return [rg.Point3d(start_pt)]
    vec.Unitize()
    normal = rg.Vector3d.CrossProduct(vec, rg.Vector3d.ZAxis)
    normal.Unitize()
    
    # Ensuring new Point3d instances are created
    p_side = start_pt + (normal * dist *0.5)
    p_fwd = start_pt + (vec * dist)
    return [rg.Point3d(start_pt), p_side, p_fwd, rg.Point3d(start_pt)]

def create_linear_tie(pt, vector, offset_dist):
    """Generates a linear tie-in/out stitch along a vector."""
    if vector.IsZero: vector = rg.Vector3d.XAxis
    vector.Unitize()
    p_pre  = pt - (vector * offset_dist)
    p_post = pt + (vector * offset_dist)
    return [rg.Point3d(pt), p_post, p_pre, rg.Point3d(pt)]

def create_corner_tie(pt, vec_in, vec_out, offset_dist):
    """Generates a corner tie-in/out stitch based on incoming and outgoing vectors."""
    if vec_in.IsZero: vec_in = rg.Vector3d.XAxis
    if vec_out.IsZero: vec_out = rg.Vector3d.XAxis
    vec_in.Unitize(); vec_out.Unitize()
    p_pre = pt - (vec_in * offset_dist)
    p_post = pt + (vec_out * offset_dist)
    return [rg.Point3d(pt), p_post, p_pre, rg.Point3d(pt)]

# =========================================================
# Main Logic
# =========================================================

# 1. Prepare attributes
typs_colors = [(t, c) for t, c in zip(sorted_types, sorted_colors)] # type: ignore
dressed_pts_nested = []

# 2. Geometry Pre-processing (Generate EMB ties and WIN endpoints)
for i, (typ_color, pts) in enumerate(zip(typs_colors, pts_nested)):
    current_typ = typ_color[0]
    current_pts = [rg.Point3d(p) for p in list(pts)]
    seg_len = len(current_pts)
    processed_segment = []

    if current_typ in THREAD_STITCH_TYPES:
        for j, pt in enumerate(current_pts):
            # Handle Start/End Caps
            if j == 0:
                processed_segment.extend(create_cap_pts(pt, current_pts[j+1], TIE_OFFSET*0.1) if seg_len > 1 else [pt])
                continue
            elif j == seg_len - 1:
                processed_segment.extend(create_cap_pts(pt, current_pts[j-1], TIE_OFFSET*0.1) if seg_len > 1 else [pt])
                continue

            # Anchor Tie Check (Checking for jumps)
            prev_pt, next_pt = current_pts[j-1], current_pts[j+1]
            dist_in, dist_out = prev_pt.DistanceTo(pt) * 10, pt.DistanceTo(next_pt) * 10
            
            if dist_in > JUMP_THRESHOLD or dist_out > JUMP_THRESHOLD:
                if dist_in > JUMP_THRESHOLD and dist_out > JUMP_THRESHOLD:
                    processed_segment.extend(create_corner_tie(pt, pt-prev_pt, next_pt-pt, TIE_OFFSET*0.1))
                elif dist_in > JUMP_THRESHOLD:
                    processed_segment.extend(create_linear_tie(pt, pt-prev_pt, TIE_OFFSET*0.1))
                else:
                    processed_segment.extend(create_linear_tie(pt, next_pt-pt, TIE_OFFSET*0.1))
            else:
                processed_segment.append(pt)

    elif current_typ in CABLE_STOP_TYPES:
        # processed_segment.extend([rg.Point3d(p) for p in current_pts])
        if seg_len > 1:
            # 1. Process intermediate points (Ensuring each point is a unique instance)
            processed_segment.extend([rg.Point3d(p) for p in current_pts[:-1]])
            
            # 2. Process last point (Creating 1 point with identical coords but different memory addresses)
            last_pt = current_pts[-1]
            p_end1 = rg.Point3d(last_pt) # Clone A
            # p_end2 = rg.Point3d(last_pt) # Clone B
            
            processed_segment.append(p_end1)
            # processed_segment.append(p_end2)
        else:
            processed_segment.append(rg.Point3d(current_pts[0]))

    dressed_pts_nested.append(processed_segment)

# 3. Process Travel Paths (Generated in the original coordinate system)
travel_pts_nested = []
for i, pts in enumerate(dressed_pts_nested):
    # Initial travel from home
    if i == 0:
        p1, p3 = origin + jump_vec, rg.Point3d(pts[0].X, pts[0].Y, 0) + jump_vec
        travel_pts_nested.append([p1, (p1 + p3) / 2, p3])
    
    # Inter-segment travel
    if i < len(dressed_pts_nested) - 1:
        t1 = rg.Point3d(pts[-1].X, pts[-1].Y, 0) + jump_vec
        t3 = rg.Point3d(dressed_pts_nested[i+1][0].X, dressed_pts_nested[i+1][0].Y, 0) + jump_vec
        travel_pts_nested.append([t1, (t1 + t3) / 2, t3])
    
    # Final travel back to home
    if i == len(dressed_pts_nested) - 1:
        h1, h3 = rg.Point3d(pts[-1].X, pts[-1].Y, 0) + jump_vec, origin + jump_vec
        travel_pts_nested.append([h1, (h1 + h3) / 2, h3])

# 4. Merge into a single preview list
zip_pts_preview = []
for trav, dress in zip_longest(travel_pts_nested, dressed_pts_nested):
    if trav: zip_pts_preview.append(trav)
    if dress: zip_pts_preview.append(dress)

# 5. Store into OrderedDict (Mpt.X, pt.Y now reflect mirrored values)
xform = rg.Transform.Mirror(rg.Plane.WorldYZ)
sid = -1
final_ordered_dict = OrderedDict([("STITCH_INDEX", []), ("PATH_INDEX", []), ("X", []), ("Y", []), ("COLOR", []), ("TYPE", [])])
for pid, (pts_list, info) in enumerate(zip(dressed_pts_nested, typs_colors)):
    for pt in pts_list:
        sid += 1
        mirrored_pt = rg.Point3d(pt.X, pt.Y, 0.0)
        if MIRROR:
            mirrored_pt.Transform(xform)
        final_ordered_dict["STITCH_INDEX"].append(sid)
        final_ordered_dict["PATH_INDEX"].append(pid)
        final_ordered_dict["X"].append(mirrored_pt.X)
        final_ordered_dict["Y"].append(mirrored_pt.Y)
        final_ordered_dict["COLOR"].append(info[1])
        final_ordered_dict["TYPE"].append(info[0])

# 6. Outputs
zpts_tree = th.list_to_tree(zip_pts_preview)
out_dict = final_ordered_dict