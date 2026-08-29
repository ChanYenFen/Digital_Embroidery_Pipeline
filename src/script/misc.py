import array


# --- Marshaling helpers for the native curve_sort DLL (CPython 3) ---
 
 
def curves_to_endpoint_buffer(curves):
    """Flatten endpoints to a flat double buffer: [sx,sy,sz, ex,ey,ez, ...]. Returns (buffer, n)."""
    buf = array.array('d')
    for c in curves:
        s = c.PointAtStart
        e = c.PointAtEnd
        buf.append(s.X)
        buf.append(s.Y)
        buf.append(s.Z)
        buf.append(e.X)
        buf.append(e.Y)
        buf.append(e.Z)
    return buf, len(curves)
 
 
def start_pt_to_buffer(start_pt):
    """Flatten the reference start point to a 3-double buffer [X, Y, Z]."""
    return array.array('d', (start_pt.X, start_pt.Y, start_pt.Z))
 
 
def apply_order(curves, order, reversal):
    """Rebuild ordered curves from native result. Duplicate/Reverse deferred to here."""
    out = []
    for idx, rev in zip(order, reversal):
        c = curves[idx].Duplicate()
        if rev:
            c.Reverse()
        out.append(c)
    return out


def travel_points_from_buffer(buf, n):
    """Rebuild travel-segment endpoints from the native out_travel_points buffer.
    Returns a list of n (start, end) Point3d tuples."""
    import Rhino.Geometry as rg
    out = []
    for i in range(n):
        base = i * 6
        start = rg.Point3d(buf[base],     buf[base + 1], buf[base + 2])
        end   = rg.Point3d(buf[base + 3], buf[base + 4], buf[base + 5])
        out.append((start, end))
    return out
