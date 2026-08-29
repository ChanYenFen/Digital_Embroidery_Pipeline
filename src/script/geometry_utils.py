"""
Path Optimization Module for D2M Project
Focus: Geometric path sorting for embroidery and CNC toolpaths.
"""

__author__ = "Yen-Fen Chan"
__date__ = "2026.03.05"
__update__ = "2026.07.04"

import ctypes

import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th

import misc

# from _reload import unload_modules
# unload_modules("native_bridge")
import native_bridge


def _get_entry_exit(curve, rev):
    """Returns the (entry_point, exit_point) of a curve given its reversal state."""
    if rev:
        return curve.PointAtEnd, curve.PointAtStart
    else:
        return curve.PointAtStart, curve.PointAtEnd


def _two_opt_improve(curves, ordered_indices, reversals, max_passes=10):
    """
    2-opt post-processing: attempts to reverse sub-sequences to reduce total jump distance.

    For each pair (i, j), compares the cost of edges:
        i -> i+1  and  j -> j+1
    against the cost after reversing the sub-sequence i+1 ~ j:
        i -> j    and  i+1 -> j+1

    Accepts the swap if the new cost is strictly lower.

    Time Complexity: O(passes * n^2)

    Args:
        curves (list[rg.Curve])      : Original curve list (unmodified).
        ordered_indices (list[int])  : Current sorted indices.
        reversals (list[bool])       : Reversal flags corresponding to ordered_indices.
        max_passes (int)             : Maximum number of improvement passes.

    Returns:
        tuple: (improved ordered_indices, improved reversals)
    """
    n = len(ordered_indices)
    indices = list(ordered_indices)
    revs = list(reversals)
    improved = True
    passes = 0

    while improved and passes < max_passes:
        improved = False
        passes += 1

        for i in range(n - 1):
            for j in range(i + 2, n):
                # Current cost: edge i->i+1 and edge j->j+1
                _, exit_i     = _get_entry_exit(curves[indices[i]],     revs[i])
                entry_i1, _   = _get_entry_exit(curves[indices[i + 1]], revs[i + 1])
                _, exit_j     = _get_entry_exit(curves[indices[j]],     revs[j])

                cost_before = exit_i.DistanceTo(entry_i1)
                if j + 1 < n:
                    entry_j1, _ = _get_entry_exit(curves[indices[j + 1]], revs[j + 1])
                    cost_before += exit_j.DistanceTo(entry_j1)

                # Proposed cost after reversing sub-sequence i+1 ~ j
                # New edge 1: exit_i -> exit_j (j becomes the new i+1, flipped)
                # New edge 2: entry_i1 -> entry_j1 (i+1 becomes the new j, flipped)
                cost_after = exit_i.DistanceTo(exit_j)
                if j + 1 < n:
                    cost_after += entry_i1.DistanceTo(entry_j1)

                if cost_after < cost_before - 1e-6:
                    # Reverse sub-sequence: flip order and negate reversal flags
                    indices[i + 1:j + 1] = indices[i + 1:j + 1][::-1]
                    revs[i + 1:j + 1]    = [not r for r in revs[i + 1:j + 1][::-1]]
                    improved = True

    return indices, revs


def sort_curves_by_rtree(curves, start_pt=rg.Point3d(0, 0, 0), use_two_opt=False, two_opt_max_passes=10):
    """
    Performs a greedy nearest-neighbor sorting on a list of curves using an R-Tree index,
    with an optional 2-opt post-processing pass to reduce total jump distance.

    Args:
        curves (list[rg.Curve])  : The input curves to be sorted.
        start_pt (rg.Point3d)    : The reference point to find the first curve. Default is (0,0,0).
        use_two_opt (bool)       : Whether to run 2-opt improvement after greedy sort. Default is False.
        two_opt_max_passes (int) : Maximum number of 2-opt passes. Default is 10.
                                   For large sets (>3000 curves), consider setting this to 1 or 2.

    Returns:
        tuple: (list of sorted rg.Curve, list of original indices)
    """
    if not curves:
        return [], []

    # 1. Initialize R-Tree and point-to-id mapping
    # Even IDs for StartPoint, Odd IDs for EndPoint
    id_to_point = {}
    rtree = rg.RTree()

    for i, c in enumerate(curves):
        start_id = i * 2
        end_id   = i * 2 + 1

        rtree.Insert(c.PointAtStart, start_id)
        rtree.Insert(c.PointAtEnd,   end_id)

        id_to_point[start_id] = c.PointAtStart
        id_to_point[end_id]   = c.PointAtEnd

    # 2. Find the starting curve (closest endpoint to the provided start_pt)
    first_idx          = -1
    min_dist_to_origin = float("inf")
    first_is_rev       = False

    for i, c in enumerate(curves):
        d_s = start_pt.DistanceTo(c.PointAtStart)
        d_e = start_pt.DistanceTo(c.PointAtEnd)

        if d_s < min_dist_to_origin:
            min_dist_to_origin = d_s
            first_idx          = i
            first_is_rev       = False
        if d_e < min_dist_to_origin:
            min_dist_to_origin = d_e
            first_idx          = i
            first_is_rev       = True

    # Containers for the sorted sequence
    ordered_indices = [first_idx]
    reversals       = [first_is_rev]
    used_indices    = {first_idx}

    # Track the current exit point of the path
    last_pt = curves[first_idx].PointAtStart if first_is_rev else curves[first_idx].PointAtEnd

    # 3. Greedy search using R-Tree
    # Time Complexity: O(n log n)
    best_match = {"dist": float("inf"), "idx": -1, "rev": False}

    def rtree_callback(sender, e):
        idx = e.Id // 2
        if idx in used_indices:
            return
        dist = last_pt.DistanceTo(id_to_point[e.Id])
        if dist < best_match["dist"]:
            best_match["dist"] = dist
            best_match["idx"] = idx
            best_match["rev"] = (e.Id % 2 == 1)

    while len(ordered_indices) < len(curves):

        best_match["dist"] = float("inf")
        best_match["idx"] = -1
        best_match["rev"] = False

        # Search within a large bounding sphere
        rtree.Search(rg.Sphere(last_pt, 1000000), rtree_callback)

        next_idx = best_match["idx"]
        if next_idx == -1:
            break  # Safety break to prevent infinite loops

        used_indices.add(next_idx)
        ordered_indices.append(next_idx)

        need_rev = best_match["rev"]
        reversals.append(need_rev)

        # Update last_pt to the exit end of the next curve
        next_curve = curves[next_idx]
        last_pt    = next_curve.PointAtStart if need_rev else next_curve.PointAtEnd

    # 4. Optional: 2-opt post-processing to reduce total jump distance
    # Recommended for curve counts under ~3000; use max_passes=1~2 for larger sets
    if use_two_opt and len(ordered_indices) > 3:
        ordered_indices, reversals = _two_opt_improve(
            curves, ordered_indices, reversals, max_passes=two_opt_max_passes
        )

    # 5. Reconstruct and return geometry
    # Reversing curves only at the final step to minimize memory overhead
    ordered_curves = []
    for idx, rev in zip(ordered_indices, reversals):
        new_c = curves[idx].Duplicate()
        if rev:
            new_c.Reverse()
        ordered_curves.append(new_c)

    return ordered_curves, ordered_indices


# ===========================================================================
# Native (C++) backend: same greedy + 2-opt, sorted in curve_sort.dll.
# Drop-in replacement for sort_curves_by_rtree with an added knn_k parameter.
# DLL loading / ctypes signature binding lives in native_bridge.py.
# ===========================================================================


def sort_curves_native(curves, start_pt=rg.Point3d(0, 0, 0),
                       use_two_opt=False, two_opt_max_passes=10, knn_k=12,
                       if_flip=True, return_travel_points=False):
    """C++-backed drop-in replacement for sort_curves_by_rtree.

    Same inputs/outputs; `knn_k` controls how many neighbors the greedy step
    queries per hop (8-16 is typical). `if_flip=False` fixes curve direction
    (connect head->tail only): reversal stays 0 and 2-opt is skipped. 2-opt
    itself switches from exhaustive O(n^2) to a windowed kd-tree search above
    ~10000 curves (see curve_sort.cpp).

    Returns (sorted curves, original indices). With `return_travel_points=True`,
    returns a 3rd element: a list of n (start, end) Point3d tuples for the
    native inter-curve travel path (start_pt -> first curve, then each
    curve's exit -> the next curve's entry).
    """
    if not curves:
        return ([], [], []) if return_travel_points else ([], [])

    lib = native_bridge.load_dll()

    # Marshal geometry -> flat double buffers (zero-copy views for ctypes).
    buf, n = misc.curves_to_endpoint_buffer(curves)
    sp     = misc.start_pt_to_buffer(start_pt)

    endpoints_ptr = (ctypes.c_double * len(buf)).from_buffer(buf)
    start_ptr     = (ctypes.c_double * 3).from_buffer(sp)

    # Output buffers the DLL fills in.
    out_order    = (ctypes.c_int * n)()
    out_reversal = (ctypes.c_int * n)()
    out_travel   = (ctypes.c_double * (n * 6))()

    lib.sort_curves(
        endpoints_ptr,
        n,
        start_ptr,
        1 if use_two_opt else 0,
        two_opt_max_passes,
        knn_k,
        1 if if_flip else 0,
        out_order,
        out_reversal,
        out_travel,
    )

    order    = list(out_order)
    reversal = list(out_reversal)

    ordered_curves = misc.apply_order(curves, order, reversal)

    if not return_travel_points:
        return ordered_curves, order

    travel_points = misc.travel_points_from_buffer(out_travel, n)
    return ordered_curves, order, travel_points


if __name__ == "__main__":
    from functools import partial

    nested_groups = th.tree_to_list(curves_tree)  # type: ignore

    final_nested_curves = []   # [[sorted_group0], [sorted_group1], ...]
    all_flattened_curves = []  # [crv, crv, crv, ...]

    current_start_pt = rg.Point3d(0, 0, 0)

    KNN_K      = 12
    USE_2OPT   = True
    MAX_PASSES = 10

    # Always sort with the native backend; fall back to the pure-Python R-Tree
    # sorter only if the DLL can't be loaded (missing/locked, other platform).
    try:
        native_bridge.load_dll()
        sort_curves_func = partial(sort_curves_native,
                                   use_two_opt=USE_2OPT,
                                   two_opt_max_passes=MAX_PASSES,
                                   knn_k=KNN_K,
                                   if_flip=if_flip)  # type: ignore
    except Exception as e:
        print("native curve_sort unavailable, falling back to R-Tree: %s" % e)
        sort_curves_func = partial(sort_curves_by_rtree,
                                   use_two_opt=USE_2OPT,
                                   two_opt_max_passes=MAX_PASSES)

    for i, group in enumerate(nested_groups):
        # Sort the current group, using the end point of the previous group as start_pt
        sorted_group, _ = sort_curves_func(group, current_start_pt)

        final_nested_curves.append(sorted_group)
        all_flattened_curves.extend(sorted_group)

        # Update the start point for the next group
        if sorted_group:
            current_start_pt = sorted_group[-1].PointAtEnd

    # --- Output to Grasshopper ---
    # DataTree output (preserves group structure)
    out_curves_tree = th.list_to_tree(final_nested_curves)

    # Flat list output
    out_curves_flat = all_flattened_curves