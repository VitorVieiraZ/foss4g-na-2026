"""Fill templates/build_project.py from a JSON spec.

Usage: python3 render.py spec.json output.py [--force]

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
NAME = re.compile(r"[a-z][a-z0-9_]*")
TYPES = {"text", "integer", "decimal", "date", "datetime", "boolean"}


def check_spec(spec):
    """Catch spec mistakes here, before anyone runs the script in QGIS."""
    errors, warnings = [], []
    lists = spec.get("lookup_lists", {})
    for name in list(lists):
        if not NAME.fullmatch(name) or name.startswith(("gpkg_", "rtree_", "sqlite_")):
            errors.append(f"lookup list '{name}': use lowercase letters, numbers and _")
        if not all(isinstance(v, str) and v for v in lists[name]):
            errors.append(f"lookup list '{name}': values must be non-empty text")
    layer_names = [l.get("name", "?") for l in spec["layers"]] + list(lists)
    layer_names += [l.get("name", "?") + "_photos" for l in spec["layers"] if l.get("multiple_photos")]
    if len(layer_names) != len(set(layer_names)):
        errors.append("two layers / lookup lists / photo tables share a name")
    for layer in spec["layers"]:
        missing = [k for k in ("name", "geometry", "fields") if k not in layer]
        if missing:
            errors.append(f"a layer is missing {', '.join(missing)}")
            continue
        if not NAME.fullmatch(layer["name"]) or layer["name"].startswith(("gpkg_", "rtree_", "sqlite_")):
            errors.append(f"layer '{layer['name']}': use lowercase letters, numbers and _ (not gpkg_/rtree_/sqlite_)")
        bad = [f for f in layer["fields"] if "name" not in f or "type" not in f]
        if bad:
            errors.append(f"{layer['name']}: every field needs a 'name' and a 'type'")
            continue
        if layer.get("geometry") not in ("point", "line", "polygon", "none"):
            errors.append(f"{layer['name']}: geometry must be point, line, polygon or none")
        names = [f["name"] for f in layer["fields"]]
        if layer.get("title") and layer["title"] not in names + ["uuid"]:
            errors.append(f"{layer['name']}: title '{layer['title']}' is not one of its fields")
        for f in layer["fields"]:
            where = f"{layer['name']}.{f['name']}"
            widget = f.get("widget", "text")
            if f["type"] not in TYPES:
                errors.append(f"{where}: type must be one of {sorted(TYPES)}")
            if not NAME.fullmatch(f["name"]):
                errors.append(f"{where}: use lowercase letters, numbers and _")
            if f["name"] in AUTOMATIC or f["name"].startswith("spare_"):
                errors.append(f"{where}: name is reserved for an automatic field")
            if widget not in WIDGET_TYPES:
                errors.append(f"{where}: unknown widget '{widget}'")
            elif WIDGET_TYPES[widget] and f["type"] not in WIDGET_TYPES[widget]:
                errors.append(f"{where}: widget '{widget}' needs type {sorted(WIDGET_TYPES[widget])}")
            if "min" in f and "max" in f and f["min"] > f["max"]:
                errors.append(f"{where}: min is bigger than max")
            if widget == "hidden" and f.get("required") and not f.get("default"):
                errors.append(f"{where}: a hidden required field with no default can never be filled")
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


SAFE = {
    # Values pasted into the script as code: only allow what they need.
    "project_name": (r"^[a-z0-9][a-z0-9_-]{0,59}$", "lowercase letters, numbers, - and _"),
    "crs": (r"^[A-Za-z]+:[0-9A-Za-z_]+$", "like EPSG:4326"),
    "qgis_version": (r"^[0-9]+(\.[0-9x]+)*$", "like 3.42"),
}


def check_settings(spec):
    """Refuse anything that could break the script or point it elsewhere."""
    errors = []
    for key, (pattern, hint) in SAFE.items():
        if key in spec and not re.fullmatch(pattern.strip("^$"), str(spec[key])):
            errors.append(f"{key}: {spec[key]!r} is not allowed ({hint})")
    folder = spec.get("parent_folder", "MerginMaps Projects")
    if (os.path.isabs(folder) or ".." in folder.replace("\\", "/").split("/")
            or not re.fullmatch(r"[\w .\-/]+", folder) or folder.lstrip("/").startswith(".")
            or folder.split("/")[0] in ("Library", "AppData")):
        errors.append(f"parent_folder: {folder!r} must be a simple folder inside your home folder")
    if re.search(r"onedrive|dropbox|google ?drive|icloud", folder, re.I):
        print("Warning: parent_folder is a cloud-synced folder; GeoPackages can get corrupted there. "
              "Use a plain local folder.")
    if spec.get("mode", "new") not in ("new", "add"):
        errors.append("mode must be 'new' or 'add'")
    if spec.get("background", "mergin") not in ("mergin", "osm", None):
        errors.append("background must be 'mergin', 'osm' or null")
    pq, sn = spec.get("photo_quality", 1), spec.get("snapping", 0)
    if type(pq) is not int or pq not in (0, 1, 2, 3) or type(sn) is not int or sn not in (0, 1, 2):
        errors.append("photo_quality must be 0-3 and snapping 0-2")
    for layer in spec["layers"]:
        if "color" in layer and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(layer["color"])):
            errors.append(f"{layer['name']}: color must look like #1db278")
    aoi = (spec.get("area_of_interest") or {}).get("bbox")
    if aoi is not None and not (len(aoi) == 4 and all(isinstance(v, (int, float)) for v in aoi)
                                and -180 <= aoi[0] < aoi[2] <= 180 and -90 <= aoi[1] < aoi[3] <= 90):
        errors.append("area_of_interest.bbox must be [west, south, east, north] in degrees")
    if errors:
        sys.exit("Spec problems:\n  - " + "\n  - ".join(errors))


def plain(text):
    """Text for comments/docstrings: one line, no quotes or backslashes."""
    return re.sub(r'["\\\n\r]', "", str(text))[:80]


def main(spec_path, out_path, force=False):
    spec = json.load(open(spec_path, encoding="utf-8"))
    check_settings(spec)
    check_spec(spec)
    skill_dir = os.path.realpath(os.path.join(HERE, ".."))
    target = os.path.realpath(out_path)
    if not target.endswith(".py"):
        sys.exit("render.py: the output must be a .py file")
    if target.startswith(skill_dir + os.sep):
        sys.exit("render.py: don't write into the skill's own folder")
    if os.path.exists(target) and not force:
        sys.exit(f"render.py: {out_path} exists. Pass --force to replace it.")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    aoi = spec.get("area_of_interest")
    values = {
        "PROJECT_TITLE": plain(spec.get("title", spec["project_name"])),
        "MODE": spec.get("mode", "new"),
        "PROJECT_NAME": spec["project_name"],
        "PARENT_FOLDER": spec.get("parent_folder", "MerginMaps Projects"),
        "CRS": spec.get("crs", "EPSG:4326"),
        "AREA_OF_INTEREST": (py(aoi["bbox"]) + f"  # {plain(aoi.get('label', ''))}") if aoi else "None",
        "BACKGROUND": str(spec.get("background", "mergin")),
        "PHOTO_QUALITY": str(spec.get("photo_quality", 1)),
        "SNAPPING": str(spec.get("snapping", 0)),
        "LOOKUP_LISTS": py(spec.get("lookup_lists", {})),
        "LAYERS": py(spec["layers"]),
        "QGIS_VERSION": str(spec.get("qgis_version", "3.x")),
        "DATE": datetime.date.today().isoformat(),
    }
    text = open(TEMPLATE).read()
    if spec.get("background", "mergin") is None:
        text = text.replace('"{{BACKGROUND}}"', "None")
    # One pass over the TEMPLATE only, so text inside the spec is never expanded.
    unknown = set(re.findall(r"\{\{([A-Z_]+)\}\}", text)) - set(values)
    if unknown:
        sys.exit(f"render.py: template placeholders without a value: {sorted(unknown)}")
    text = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values[m.group(1)], text)
    compile(text, out_path, "exec")  # fail early on a syntax error
    with open(target, "w", encoding="utf-8") as out:
        out.write(text)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 2:
        sys.exit("Usage: python3 render.py spec.json output.py [--force]")
    main(args[0], args[1], force="--force" in sys.argv)
