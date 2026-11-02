"""Fill templates/build_project.py from a JSON spec.

Usage: python3 render.py spec.json output.py

The spec holds the answers gathered from the user (see SKILL.md, "Spec").
Missing optional keys get the agreed defaults (EPSG:4326, mergin background,
High photo quality, no snapping).
"""
import datetime
import json
import os
import pprint
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "templates", "build_project.py")


def py(value):
    """Pretty Python literal, indented like hand-written settings."""
    return pprint.pformat(value, indent=4, width=100, sort_dicts=False)


AUTOMATIC = {"fid", "uuid", "created_at", "created_by", "updated_at", "updated_by", "gps_accuracy"}
WIDGET_TYPES = {
    "text": None, "notes": {"text"}, "hidden": None,
    "dropdown": {"text", "integer"}, "lookup": {"text"}, "photo": {"text"},
    "number": {"integer", "decimal"}, "checkbox": {"boolean"}, "date": {"date", "datetime"},
}
NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def check_spec(spec):
    """Catch spec mistakes here, before anyone runs the script in QGIS."""
    errors, warnings = [], []
    lists = spec.get("lookup_lists", {})
    for layer in spec["layers"]:
        if layer.get("geometry") not in ("point", "line", "polygon", "none"):
            errors.append(f"{layer['name']}: geometry must be point, line, polygon or none")
        names = [f["name"] for f in layer["fields"]]
        if layer.get("title") and layer["title"] not in names + ["uuid"]:
            errors.append(f"{layer['name']}: title '{layer['title']}' is not one of its fields")
        for f in layer["fields"]:
            where = f"{layer['name']}.{f['name']}"
            widget = f.get("widget", "text")
            if not NAME.match(f["name"]):
                errors.append(f"{where}: use lowercase letters, numbers and _")
            if f["name"] in AUTOMATIC or f["name"].startswith("spare_"):
                errors.append(f"{where}: name is reserved for an automatic field")
            if widget not in WIDGET_TYPES:
                errors.append(f"{where}: unknown widget '{widget}'")
            elif WIDGET_TYPES[widget] and f["type"] not in WIDGET_TYPES[widget]:
                errors.append(f"{where}: widget '{widget}' needs type {sorted(WIDGET_TYPES[widget])}")
            if widget == "number" and ("min" not in f or "max" not in f):
                warnings.append(f"{where}: number without min/max (sliders break: mobile#1516). Add both.")
            if f.get("default") and re.search(r'"[a-z]', f["default"]):
                warnings.append(f"{where}: default refers to another field; may not apply on new features (mobile#4417)")
            if widget == "dropdown" and not f.get("choices"):
                errors.append(f"{where}: dropdown needs choices")
            rule = f.get("constraint")
            if rule is not None and not (isinstance(rule, dict) and rule.get("expression")):
                errors.append(f"{where}: constraint needs an 'expression' (and a 'message')")
            elif rule and not rule.get("message"):
                errors.append(f"{where}: constraint needs a 'message' to show in the app")
            if widget == "lookup" and f.get("list") not in lists:
                errors.append(f"{where}: lookup list '{f.get('list')}' is not in lookup_lists")
        if len(names) != len(set(names)):
            errors.append(f"{layer['name']}: duplicate field names")
        if layer.get("multiple_photos"):
            if layer.get("geometry") == "none":
                errors.append(f"{layer['name']}: multiple_photos needs a map layer (point/line/polygon)")
            if any(f.get("widget") == "photo" for f in layer["fields"]):
                warnings.append(f"{layer['name']}: has a single photo field AND multiple_photos; the app can "
                                "overwrite the single photo with gallery photos (mobile#2029). Use only one.")
    for w in warnings:
        print("Warning:", w)
    if errors:
        sys.exit("Spec problems:\n  - " + "\n  - ".join(errors))


def main(spec_path, out_path):
    spec = json.load(open(spec_path))
    check_spec(spec)
    aoi = spec.get("area_of_interest")
    values = {
        "PROJECT_TITLE": spec.get("title", spec["project_name"]),
        "PROJECT_NAME": spec["project_name"],
        "PARENT_FOLDER": spec.get("parent_folder", "MerginMaps Projects"),
        "CRS": spec.get("crs", "EPSG:4326"),
        "AREA_OF_INTEREST": (py(aoi["bbox"]) + f"  # {aoi.get('label', '')}") if aoi else "None",
        "BACKGROUND": spec.get("background", "mergin"),
        "PHOTO_QUALITY": str(spec.get("photo_quality", 1)),
        "SNAPPING": str(spec.get("snapping", 0)),
        "LOOKUP_LISTS": py(spec.get("lookup_lists", {})),
        "LAYERS": py(spec["layers"]),
        "QGIS_VERSION": spec.get("qgis_version", "3.x"),
        "DATE": datetime.date.today().isoformat(),
    }
    text = open(TEMPLATE).read()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    if values["BACKGROUND"] == "None":
        text = text.replace('BACKGROUND = "None"', "BACKGROUND = None")
    if "{{" in text:
        sys.exit("render.py: a placeholder was left unfilled")
    compile(text, out_path, "exec")  # fail early on a syntax error
    open(out_path, "w").write(text)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
