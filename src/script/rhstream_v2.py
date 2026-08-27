__author__ = "fen.chan"
__version__ = "2024.05.14"
__update__ = "2026.08.26"

import System
import Rhino
import Rhino.Geometry as rg
import Grasshopper
import scriptcontext as sc
import ghpythonlib.treehelpers as th
from typing import NamedTuple, List, Optional, Tuple
from collections import OrderedDict

# ==============================================================================
# 1. Settings Parser (Data Structure)
# ==============================================================================

class LayerSettings(NamedTuple):
    """
    Parses and holds embroidery settings from a layer name string.
    Format: Order_Type_Color_Pattern_Len_Wid_Comment
    """
    order: int
    type_code: str
    color_id: int
    pattern_id: int
    stitch_len: float
    pattern_wid: float
    comment: str

    @classmethod
    def from_string(cls, layer_name: str) -> Optional['LayerSettings']:
        parts = layer_name.split('_')
        if len(parts) < 6:
            return None
        try:
            return cls(
                order       = int(parts[0]),
                type_code   = parts[1],
                color_id    = int(parts[2]),
                pattern_id  = int(parts[3]),
                stitch_len  = float(parts[4]) * 0.1,
                pattern_wid = float(parts[5]) * 0.1,
                comment     = "_".join(parts[6:]) if len(parts) > 6 else ""
            )
        except ValueError:
            return None

# ==============================================================================
# 2. Main Stream Class
# ==============================================================================

class RhStream:
    RHINO_DOC = Rhino.RhinoDoc.ActiveDoc

    def __init__(self, referenced_guids: List[System.Guid]):
        self.RH_guids = referenced_guids
        self.valid_pairs = []  # Holds (Curve, LayerName, LayerSettings)

        # Will be populated during extraction
        self.unique_orders = set()
        self.curve_counts = {}

    def _extract_rhino_objects(self):
        if not self.RH_guids:
            return []

        extracted_data = []
        for guid in self.RH_guids:
            rh_obj = self.RHINO_DOC.Objects.Find(guid)
            if rh_obj is None:
                continue

            # 優先讀 Object Name（SVG 匯入時 <g> id 會寫到這裡）
            # 若無 Object Name 則 fallback 到 Layer Name
            obj_name = rh_obj.Attributes.Name
            if obj_name:
                # print("read o name",obj_name)
                source_name = obj_name
            else:
                layer_index = rh_obj.Attributes.LayerIndex
                source_name = self.RHINO_DOC.Layers[layer_index].Name

            geometry = rh_obj.Geometry

            if isinstance(geometry, rg.Curve):
                extracted_data.append((geometry, source_name))
        return extracted_data

    def _init_sticky_parameters(self):
        """Initializes or retrieves the sticky dictionary based on parsed orders."""
        self.overwrite_parameters = sc.sticky.get('overwrite_parameters', {})

        # Ensure all current orders exist in the sticky dict
        for order in self.unique_orders:
            if order not in self.overwrite_parameters:
                self.overwrite_parameters[order] = {
                    "parameters": {"order": order,"type_code": None,
                                   "color_id": None, "pattern_id": None,
                                   "stitch_len": None, "pattern_wid": None,
                                   "comment": None},
                    "overwritten": False
                }
        # Update sticky globally
        sc.sticky['overwrite_parameters'] = self.overwrite_parameters

    def save_overwritten(self, name_str: str):
        """Updates sticky with new parameters from a string (e.g., '0_EMB_1_3_50_50_jig')"""
        params = name_str.split("_")
        if len(params) < 6:
            print("Overwrite failed: Parameter string format incorrect.")
            return

        try:
            ix = int(params[0])
            if ix in self.overwrite_parameters:
                self.overwrite_parameters[ix]["parameters"]["order"] = ix
                self.overwrite_parameters[ix]["parameters"]["type_code"] = str(params[1])
                self.overwrite_parameters[ix]["parameters"]["color_id"] = int(params[2])
                self.overwrite_parameters[ix]["parameters"]["pattern_id"] = int(params[3])
                self.overwrite_parameters[ix]["parameters"]["stitch_len"] = float(params[4]) * 0.1
                self.overwrite_parameters[ix]["parameters"]["pattern_wid"] = float(params[5]) * 0.1
                self.overwrite_parameters[ix]["parameters"]["comment"] = "_".join(params[6:]) if len(params) > 6 else ""

                self.overwrite_parameters[ix]["overwritten"] = True
                sc.sticky['overwrite_parameters'] = self.overwrite_parameters
                print("Successfully overwritten parameters for Layer Order: {}".format(ix))
        except ValueError:
            print("Overwrite failed: Could not parse numerical values.")

    def reset_overwrite_parameters(self):
        """Clears the overwrite status for all tracked orders."""
        if hasattr(self, 'overwrite_parameters'):
            for ix in self.overwrite_parameters:
                self.overwrite_parameters[ix]["overwritten"] = False
            sc.sticky['overwrite_parameters'] = self.overwrite_parameters
            print("overwrite_parameters have been reset to original layer settings.")

    def group_curves_by_indices(self, curves, indices):
        if len(curves) != len(indices):
            raise ValueError("The number of curves must match the number of indices.")
        groups = {}
        for i, group_idx in enumerate(indices):
            if group_idx not in groups:
                groups[group_idx] = []
            groups[group_idx].append(curves[i])

        sorted_keys = sorted(groups.keys())
        return [groups[key] for key in sorted_keys]

    def display_info(self):
        divider = 80
        print("Imported Design Information")
        print("{}".format("=" * divider))
        print("{}".format(" " * divider))

        for order in sorted(self.unique_orders):
            is_overwritten = self.overwrite_parameters[order]["overwritten"]

            # Find the original settings for this order to display
            orig_settings = next((p[2] for p in self.valid_pairs if p[2].order == order), None)

            print("Layer Order: {}".format(order))

            print("Curve Count : {}".format(self.curve_counts.get(order, 0)))
            print("Overwritten : {}".format(is_overwritten))

            if is_overwritten:
                print("Active Params: {}".format(self.overwrite_parameters[order]["parameters"]))
                # print("Orig. Params : {}".format(orig_settings._asdict() if orig_settings else "None"))
            else:
                print("Active Params: {}".format(orig_settings._asdict() if orig_settings else "None"))

            print("{}".format(" " * divider))
            print("{}".format("-" * divider))
            print("{}".format(" " * divider))
        print("Done.")

    def get_data(self, toSort: bool, reload_input: bool) -> Tuple[list, ...]:
        if reload_input or not self.RH_guids:
            return (None,) * 8

        self.valid_pairs = []
        self.unique_orders = set()
        self.curve_counts = {}

        raw_data = self._extract_rhino_objects()

        for curve, layer_name in raw_data:
            settings = LayerSettings.from_string(layer_name)
            if settings:
                self.valid_pairs.append((curve, layer_name, settings))
                self.unique_orders.add(settings.order)
                self.curve_counts[settings.order] = self.curve_counts.get(settings.order, 0) + 1

        if not self.valid_pairs:
            return ([], [], [], [], [], [], [], [])

        self._init_sticky_parameters()

        if toSort:
            self.valid_pairs.sort(key=lambda x: x[2].order)

        sorted_curves = []
        sorted_layer_names = []
        sorted_orders = []
        sorted_types = []
        sorted_color_ids = []
        sorted_pattern_ids = []
        sorted_stitch_lens = []
        sorted_pattern_wids = []

        for curve, layer_name, orig_settings in self.valid_pairs:
            order = orig_settings.order
            ow_data = self.overwrite_parameters.get(order, {})

            sorted_curves.append(curve)
            sorted_orders.append(order)

            if ow_data.get("overwritten"):
                p = ow_data["parameters"]

                name_parts = [
                    str(order),
                    str(p["type_code"]),
                    str(p["color_id"]),
                    str(p["pattern_id"]),
                    str(int(p["stitch_len"] * 10)),
                    str(int(p["pattern_wid"] * 10))
                ]
                if p.get("comment"):
                    name_parts.append(str(p["comment"]))

                sorted_layer_names.append("_".join(name_parts))

                sorted_types.append(p["type_code"])
                sorted_color_ids.append(p["color_id"])
                sorted_pattern_ids.append(p["pattern_id"])
                sorted_stitch_lens.append(p["stitch_len"])
                sorted_pattern_wids.append(p["pattern_wid"])
            else:
                sorted_layer_names.append(layer_name)

                sorted_types.append(orig_settings.type_code)
                sorted_color_ids.append(orig_settings.color_id)
                sorted_pattern_ids.append(orig_settings.pattern_id)
                sorted_stitch_lens.append(orig_settings.stitch_len)
                sorted_pattern_wids.append(orig_settings.pattern_wid)

        grouped_curves = self.group_curves_by_indices(sorted_curves, sorted_orders)
        tree_curves = th.list_to_tree(grouped_curves)

        return (
            tree_curves,
            sorted_layer_names,
            sorted_orders,
            sorted_types,
            sorted_color_ids,
            sorted_pattern_ids,
            sorted_stitch_lens,
            sorted_pattern_wids
        )

# ==============================================================================
# 3. Execution Block (Grasshopper)
# ==============================================================================

if __name__ == "__main__":

    out_curves = []
    out_layerNames = []
    out_orders = []
    out_types = []
    out_colors = []
    out_patterns = []
    out_stitchLens = []
    out_wids = []

    if reload_:
        sc.sticky.clear()


    elif referenced_guids:
        rhs = RhStream(referenced_guids)

        rhs.get_data(toSort=False, reload_input=reload_)

        if overwrite_:
            if save_ow and params_ow:
                name_str = "_".join(params_ow)
                rhs.reset_overwrite_parameters()
                rhs.save_overwritten(name_str)
        else:
            rhs.reset_overwrite_parameters()

        (
        out_curves,
        out_layerNames,
        out_orders,
        out_types,
        out_colors,
        out_patterns,
        out_stitchLens,
        out_wids
        ) = rhs.get_data(toSort=True, reload_input=reload_)

        rhs.display_info()
