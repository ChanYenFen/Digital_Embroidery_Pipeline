"""
svg_import_guids.py
Scans a folder for SVG files, lets user pick one by index,
imports it into Rhino, and outputs GUIDs with Object Names.

GH Inputs:
    folder_path    : str   - Directory containing SVG files
    select_ix      : int   - Index to pick from file list
    import_svg     : bool  - Button to trigger import
    refresh_folder : bool  - Rescan folder

GH Outputs:
    guids       : list[System.Guid] - Imported curve GUIDs
    names       : list[str]         - Object Names (layer naming convention)

Names are matched to curves by position, so the imported objects must be
collected in creation order. A set difference does not preserve that order,
which silently pairs names with the wrong curves - see run_svg_import below.
"""

__author__ = "fen.chan"
__version__ = "2026.08.26"

import System
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import os
from pathlib import Path
from Grasshopper.Kernel import GH_RuntimeMessageLevel as RML

STICKY_KEY = "svg_import_guids"

# ==============================================================================
# 1. Folder Scan & File Selection
# ==============================================================================

folder = Path(folder_path)
selected_path = None

if not folder.is_dir():
    ghenv.Component.AddRuntimeMessage(
        RML.Error,
        "Directory does not exist: {}".format(folder)
    )
    svg_files = []
else:
    cache_key = "SVG_LST_" + str(folder)
    if refresh_folder or cache_key not in sc.sticky:
        svg_files = sorted(p.name for p in folder.glob("*.svg"))
        sc.sticky[cache_key] = svg_files
    else:
        svg_files = sc.sticky[cache_key]

if not svg_files:
    ghenv.Component.AddRuntimeMessage(
        RML.Remark,
        "No *.svg files found in {}".format(folder)
    )
    print("[empty]  ({})".format(folder))
else:
    print("index | file name")
    print("-" * 80)
    for i, name in enumerate(svg_files):
        print("{:>5} | {}".format(i, name))

    selected_name = svg_files[select_ix % len(svg_files)]
    selected_path = os.path.join(str(folder), selected_name)
    print("")
    print("Selected: {}".format(selected_name))

# ==============================================================================
# 2. SVG Import
# ==============================================================================

def get_existing_ids(doc):
    return set(obj.Id for obj in doc.Objects)

def run_svg_import(doc, path):
    """Imports the file and returns the new objects in the order Rhino made them.

    The order matters: names are assigned to curves by index further down.
    `after - before` would be a set, whose iteration order follows GUID hashes
    and changes on every import, so the names would land on random curves.
    RuntimeSerialNumber increases with creation, so sorting on it restores
    document order.
    """
    before = get_existing_ids(doc)
    cmd = '-_Import "{}" _Enter'.format(path)
    Rhino.RhinoApp.RunScript(cmd, False)

    new_objs = [obj for obj in doc.Objects if obj.Id not in before]
    new_objs.sort(key=lambda obj: obj.RuntimeSerialNumber)
    return [obj.Id for obj in new_objs]

def set_object_names_from_svg(doc, new_guids, svg_path):
    import xml.etree.ElementTree as ET

    tree = ET.parse(svg_path)
    root = tree.getroot()

    path_ids = []
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'path':
            pid = elem.get('id', '')
            if pid:
                path_ids.append(pid)

    curve_guids = []
    for guid in new_guids:
        obj = doc.Objects.Find(guid)
        if obj and isinstance(obj.Geometry, rg.Curve):
            curve_guids.append(guid)

    # Rhino can add objects of its own on import (a frame drawn from the
    # viewBox, for one). If the counts disagree the index pairing is off, and
    # every name past that point is on the wrong curve - say so rather than
    # writing them anyway.
    if len(curve_guids) != len(path_ids):
        ghenv.Component.AddRuntimeMessage(
            RML.Warning,
            "curve count ({}) != path id count ({}); names may be misaligned".format(
                len(curve_guids), len(path_ids))
        )

    for i, guid in enumerate(curve_guids):
        if i < len(path_ids):
            obj = doc.Objects.Find(guid)
            if obj:
                attr = obj.Attributes
                attr.Name = path_ids[i]
                doc.Objects.ModifyAttributes(guid, attr, True)

    return curve_guids

# ==============================================================================
# 3. Execution
# ==============================================================================

guids = []
names = []
doc = Rhino.RhinoDoc.ActiveDoc

if import_svg and selected_path:
    if not os.path.isfile(selected_path):
        ghenv.Component.AddRuntimeMessage(
            RML.Error,
            "File not found: {}".format(selected_path)
        )
    else:
        new_guids = run_svg_import(doc, selected_path)

        if new_guids:
            curve_guids = set_object_names_from_svg(doc, new_guids, selected_path)
            sc.sticky[STICKY_KEY] = curve_guids
            print("Imported {} curves from {}".format(
                len(curve_guids), os.path.basename(selected_path)))
        else:
            print("No objects imported.")

# Always output from sticky
stored = sc.sticky.get(STICKY_KEY, [])
if stored:
    guids = stored
    names = []
    for guid in guids:
        obj = doc.Objects.Find(guid)
        if obj:
            names.append(obj.Attributes.Name or "(unnamed)")
        else:
            names.append("(deleted)")
