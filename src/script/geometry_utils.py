"""
Path Optimization Module for D2M Project
Focus: Geometric path sorting for embroidery and CNC toolpaths.
"""

__author__ = "Yen-Fen Chan"
__date__ = "2026.03.05"
__update__ = "2026.03.12"

import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th

def sort_curves_by_rtree(curves, start_pt=rg.Point3d(0, 0, 0)):
    """
    Performs a greedy nearest-neighbor sorting on a list of curves using an R-Tree index.
    
    Args:
        curves (list[rg.Curve]): The input curves to be sorted.
        start_pt (rg.Point3d): The reference point to find the first curve. Default is (0,0,0).
        
    Returns:
        tuple: (list of sorted rg.Curve, list of original indices)
    """
    if not curves:
        return [], []

    # 1. Initialize R-Tree and point-to-id mapping
    # Mapping helps retrieve point coordinates using the ID returned by R-Tree
    id_to_point = {}
    rtree = rg.RTree()
    
    for i, c in enumerate(curves):
        # Even IDs for StartPoint, Odd IDs for EndPoint
        start_id = i * 2
        end_id = i * 2 + 1
        
        rtree.Insert(c.PointAtStart, start_id)
        rtree.Insert(c.PointAtEnd, end_id)
        
        id_to_point[start_id] = c.PointAtStart
        id_to_point[end_id] = c.PointAtEnd

    # 2. Find the starting curve (closest endpoint to the provided start_pt)
    first_idx = -1
    min_dist_to_origin = float("inf")
    first_is_rev = False

    for i, c in enumerate(curves):
        d_s = start_pt.DistanceTo(c.PointAtStart)
        d_e = start_pt.DistanceTo(c.PointAtEnd)
        
        if d_s < min_dist_to_origin:
            min_dist_to_origin = d_s
            first_idx = i
            first_is_rev = False
        if d_e < min_dist_to_origin:
            min_dist_to_origin = d_e
            first_idx = i
            first_is_rev = True

    # Containers for the sorted sequence
    ordered_indices = [first_idx]
    reversals = [first_is_rev]
    used_indices = {first_idx}
    
    # Track the current exit point of the path
    last_pt = curves[first_idx].PointAtStart if first_is_rev else curves[first_idx].PointAtEnd

    # 3. Greedy search using R-Tree
    # Time Complexity: O(n log n)
    while len(ordered_indices) < len(curves):
        # Use a list to store mutable state for the callback function
        # [best_idx, best_dist, need_reverse_flag]
        best_match = [-1, float("inf"), False]

        def rtree_callback(sender, e):
            idx = e.Id // 2
            if idx in used_indices: 
                return
            
            this_pt = id_to_point[e.Id]
            dist = last_pt.DistanceTo(this_pt)
            
            if dist < best_match[1]:
                best_match[1] = dist
                best_match[0] = idx
                best_match[2] = (e.Id % 2 == 1) # True if connecting to an EndPoint

        # Search within a large bounding sphere
        rtree.Search(rg.Sphere(last_pt, 1000000), rtree_callback)

        next_idx = best_match[0]
        if next_idx == -1: 
            break # Safety break to prevent infinite loops
        
        used_indices.add(next_idx)
        ordered_indices.append(next_idx)
        
        need_rev = best_match[2]
        reversals.append(need_rev)
        
        # Update last_pt to the exit end of the next curve
        next_curve = curves[next_idx]
        last_pt = next_curve.PointAtStart if need_rev else next_curve.PointAtEnd

    # 4. Reconstruct and return geometry
    # Reversing curves only at the final step to minimize memory overhead
    ordered_curves = []
    for idx, rev in zip(ordered_indices, reversals):
        new_c = curves[idx].Duplicate()
        if rev: 
            new_c.Reverse()
        ordered_curves.append(new_c)

    return ordered_curves, ordered_indices

if __name__ == "__main__":
    nested_groups = th.tree_to_list(curves_tree) # type: ignore

    final_nested_curves = [] # To store [[sorted_group0], [sorted_group1], ...]
    all_flattened_curves = [] # To store [crv, crv, crv...] if you need a flat list
    
    current_start_pt = rg.Point3d(0, 0, 0)
    
    for i, group in enumerate(nested_groups):
        # 1. Sort the current group
        # Note: Each group uses the end point of the PREVIOUS group as its start_pt
        sorted_group, _ = sort_curves_by_rtree(group, current_start_pt)
        
        # 2. Append the sorted group as a sub-list
        final_nested_curves.append(sorted_group)
        
        # 3. Also extend the flattened list if needed
        all_flattened_curves.extend(sorted_group)
        
        # 4. Update the start_point for the NEXT group
        if sorted_group:
            current_start_pt = sorted_group[-1].PointAtEnd

    # --- Output to Grasshopper ---
    # Use final_nested_curves if you want a DataTree output
    out_curves_tree = th.list_to_tree(final_nested_curves)
    
    # Use all_flattened_curves if you want a single flat list of curves
    out_curves_flat = all_flattened_curves