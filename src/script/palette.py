"""
palette.py
Reads the stitch palette from tools/palette.js so Rhino/Grasshopper and the
browser-based SVG editor share one definition of colorID -> color.

The palette lives in a .js file (not .json) because the editor is opened via
file:// and cannot fetch() a local JSON. Rather than keeping a second copy in
sync, this module just parses the entries out of it.
"""

__author__ = "Yen-Fen Chan"
__date__ = "2026.08.26"

import io
import os
import re
from collections import OrderedDict

# src/script/palette.py -> repo root -> tools/palette.js
_HERE = os.path.dirname(os.path.abspath(__file__))
PALETTE_JS = os.path.normpath(os.path.join(_HERE, "..", "..", "tools", "palette.js"))

_ENTRY_RE = re.compile(
    r"\{\s*id:\s*(\d+)\s*,"
    r"\s*name:\s*['\"]([^'\"]*)['\"]\s*,"
    r"\s*hex:\s*['\"](#[0-9A-Fa-f]{6})['\"]\s*\}"
)

_cache_path = None
_cache_mtime = None
_cache_data = OrderedDict()


def load_palette(path=None):
    """Returns OrderedDict {id(int): {'name': str, 'hex': '#RRGGBB'}}.

    Cached on the file's mtime, so editing palette.js takes effect on the next
    call without restarting Rhino.
    """
    js_path = path or PALETTE_JS

    if not os.path.exists(js_path):
        raise IOError("palette.js not found: {}".format(js_path))

    global _cache_path, _cache_mtime, _cache_data

    mtime = os.path.getmtime(js_path)
    if _cache_path == js_path and _cache_mtime == mtime:
        return _cache_data

    # palette.js carries UTF-8 comments; don't let the OS locale (cp950 on
    # zh-TW Windows) decide the codec. utf-8-sig also tolerates a BOM.
    with io.open(js_path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    entries = OrderedDict()
    for cid, name, hex_str in _ENTRY_RE.findall(text):
        entries[int(cid)] = {"name": name, "hex": hex_str.upper()}

    if not entries:
        raise ValueError("no palette entries parsed from {}".format(js_path))

    _cache_path, _cache_mtime, _cache_data = js_path, mtime, entries
    return entries


def hex_for_id(color_id, default="#1A1A1A"):
    """colorID (int or str, 1-16) -> '#RRGGBB'."""
    try:
        cid = int(color_id)
    except (TypeError, ValueError):
        return default
    entry = load_palette().get(cid)
    return entry["hex"] if entry else default


def name_for_id(color_id, default=""):
    """colorID -> the palette's human-readable name."""
    try:
        cid = int(color_id)
    except (TypeError, ValueError):
        return default
    entry = load_palette().get(cid)
    return entry["name"] if entry else default


def hex_to_rgb(hex_str):
    """'#RRGGBB' -> (r, g, b) ints."""
    h = (hex_str or "").lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def color_for_id(color_id):
    """colorID -> System.Drawing.Color, for Grasshopper preview/bake.

    Imported lazily so this module stays readable outside Rhino.
    """
    from System.Drawing import Color
    r, g, b = hex_to_rgb(hex_for_id(color_id))
    return Color.FromArgb(r, g, b)


_RUN_NUMBER_RE = re.compile(r"_\d{2}$")


def base_layer_name(name):
    """Drops the run number the SVG editor appends when one layer holds
    several paths, recovering the layer's canonical name.

        '0_ETS_6_0_50_0_outer_03' -> '0_ETS_6_0_50_0_outer'

    SVG ids must be unique or Rhino pairs object names with the wrong curves,
    so paths in a multi-path layer are numbered; the `<g>` around them carries
    the un-numbered name. Note this also strips a description that genuinely
    ends in _NN, so avoid ending descriptions with two digits.
    """
    return _RUN_NUMBER_RE.sub("", name or "")


def color_id_from_layer_name(name, default=1):
    """Pulls colorID out of a layer name.

    Layer names are sequence_ETS_colorID_patternType_stitchLen_patternWid_description,
    so colorID is field index 2.
    """
    parts = (name or "").split("_")
    if len(parts) < 3:
        return default
    try:
        return int(parts[2])
    except ValueError:
        return default


if __name__ == "__main__":
    # Grasshopper outputs: wire these names to the component's output params.
    _entries = load_palette()

    ids    = list(_entries.keys())                      # 1..16
    names  = [v["name"] for v in _entries.values()]     # 'Black', 'White', ...
    hexes  = [v["hex"] for v in _entries.values()]      # '#1A1A1A', ...

    try:
        # Colour objects, ready for Custom Preview / any Colour input.
        colors = [color_for_id(c) for c in ids]
    except ImportError:
        colors = []  # not running inside Rhino

    for cid, info in _entries.items():
        print("{:>2}  {:<10} {}".format(cid, info["name"], info["hex"]))
