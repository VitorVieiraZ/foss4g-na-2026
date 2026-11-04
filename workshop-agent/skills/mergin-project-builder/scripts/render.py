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
    layers = spec.get("layers", [])
    layer_names = [l.get("name", "?") for l in layers] + list(lists)
    layer_names += [l.get("name", "?") + "_photos" for l in layers if l.get("multiple_photos")]
    if len(layer_names) != len(set(layer_names)):
        errors.append("two layers / lookup lists / photo tables share a name")
    for layer in spec.get("layers", []):
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
        visible = [f for f in layer["fields"] if f.get("widget", "text") != "hidden"]
        for f in visible:
            for key in ("tab", "group"):
                if key in f and not (isinstance(f[key], str) and 0 < len(f[key].strip()) <= 40):
                    errors.append(f"{layer['name']}.{f['name']}: {key} must be a short name (1-40 characters)")
        tabbed = [f["name"] for f in visible if f.get("tab")]
        if tabbed and len(tabbed) != len(visible):
            untabbed = [f["name"] for f in visible if not f.get("tab")]
            errors.append(f"{layer['name']}: some fields have a tab, these don't: {', '.join(untabbed)}")
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
    app = app_settings(spec)
    allowed = {"photo_quality": (0, 1, 2, 3), "snapping": (0, 1, 2), "tracking_frequency": (0, 1, 2),
               "layer_order": ("qgis", "alphabetical")}
    for key, values in allowed.items():
        v = app.get(key)
        if v is not None and (type(v) is bool or v not in values):
            errors.append(f"app_settings.{key} must be one of {values}")
    for key in ("position_tracking", "map_sketching", "photo_sketching", "selective_sync"):
        if app.get(key) is not None and type(app[key]) is not bool:
            errors.append(f"app_settings.{key} must be true or false")
    for color in app.get("sketch_colors") or []:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(color)):
            errors.append(f"app_settings.sketch_colors: {color!r} should look like #5e9ee4")
    if len(app.get("sketch_colors") or []) > 7:
        errors.append("app_settings.sketch_colors: at most 7 colours")
    folder_ = app.get("selective_sync_folder", "photos")
    if not re.fullmatch(r"[\w.\- /]*", str(folder_)) or ".." in str(folder_):
        errors.append("app_settings.selective_sync_folder must be a folder inside the project")
    names = {l.get("name") for l in spec.get("layers", [])}
    for f in app.get("filters") or []:
        if not isinstance(f, dict) or not f.get("layer") or not f.get("field"):
            errors.append("each filter needs 'layer' and 'field'")
        elif spec.get("mode", "new") == "new" and f["layer"] not in names:
            errors.append(f"filter: no layer called {f['layer']!r} in this spec")
    if spec.get("mode", "new") == "new" and not spec.get("layers"):
        errors.append("a new project needs at least one layer")
    for layer in spec.get("layers", []):
        if "color" in layer and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(layer["color"])):
            errors.append(f"{layer['name']}: color must look like #1db278")
    aoi = (spec.get("area_of_interest") or {}).get("bbox")
    if aoi is not None and not (len(aoi) == 4 and all(isinstance(v, (int, float)) for v in aoi)
                                and -180 <= aoi[0] < aoi[2] <= 180 and -90 <= aoi[1] < aoi[3] <= 90):
        errors.append("area_of_interest.bbox must be [west, south, east, north] in degrees")
    if errors:
        sys.exit("Spec problems:\n  - " + "\n  - ".join(errors))


FREQUENCY = {"best": 0, "normal": 1, "low": 2}


def app_settings(spec):
    """The Mergin Maps tab settings. Old specs had photo_quality/snapping at the top."""
    app = dict(spec.get("app_settings") or {})
    for key in ("photo_quality", "snapping"):
        if key in spec and key not in app:
            app[key] = spec[key]
    if isinstance(app.get("tracking_frequency"), str):
        app["tracking_frequency"] = FREQUENCY.get(app["tracking_frequency"].lower(), app["tracking_frequency"])
    return app


# Readable labels for field names: photo -> "Photo", height_m -> "Height (m)",
# needs_pruning (checkbox) -> "Needs pruning?", gps_id -> "GPS ID".
ALIAS_UNITS = {"m": "m", "cm": "cm", "mm": "mm", "km": "km", "ft": "ft", "in": "in", "mi": "mi",
               "m2": "m²", "ha": "ha", "ac": "acres", "deg": "°", "pct": "%", "percent": "%",
               "kg": "kg", "g": "g", "lb": "lb", "c": "°C", "f": "°F", "ms": "m/s", "l": "L"}
ALIAS_WORDS = {"id": "ID", "gps": "GPS", "dbh": "DBH", "uuid": "UUID", "url": "URL",
               "gis": "GIS", "qa": "QA", "qc": "QC", "ph": "pH", "no": "number"}


def default_alias(field):
    """A form label made from the field name, used when no alias is given."""
    words = field["name"].split("_")
    unit = ""
    if len(words) > 1 and words[-1] in ALIAS_UNITS:
        unit = f" ({ALIAS_UNITS[words.pop()]})"
    first_is_special = words[0] in ALIAS_WORDS
    words = [ALIAS_WORDS.get(w, w) for w in words]
    label = " ".join(words)
    if not first_is_special:  # keep "pH", "GPS" as they are
        label = label[:1].upper() + label[1:]
    if field.get("widget") == "checkbox" and not label.endswith("?"):
        label += "?"
    return label + unit


def fill_aliases(spec):
    """Give every visible field a label, so SECTION 1 shows what people will see."""
    for layer in spec.get("layers", []):
        for f in layer.get("fields", []):
            if not f.get("alias") and f.get("widget", "text") != "hidden":
                f["alias"] = default_alias(f)


def plain(text):
    """Text for comments/docstrings: one line, no quotes or backslashes."""
    return re.sub(r'["\\\n\r]', "", str(text))[:80]


def main(spec_path, out_path, force=False):
    spec = json.load(open(spec_path, encoding="utf-8"))
    check_settings(spec)
    check_spec(spec)
    fill_aliases(spec)
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
    app = app_settings(spec)
    values = {
        "PROJECT_TITLE": plain(spec.get("title", spec["project_name"])),
        "MODE": spec.get("mode", "new"),
        "PROJECT_NAME": spec["project_name"],
        "PARENT_FOLDER": spec.get("parent_folder", "MerginMaps Projects"),
        "CRS": spec.get("crs", "EPSG:4326"),
        "AREA_OF_INTEREST": (py(aoi["bbox"]) + f"  # {plain(aoi.get('label', ''))}") if aoi else "None",
        "BACKGROUND": str(spec.get("background", "mergin")),
        "PHOTO_QUALITY": repr(app.get("photo_quality")),
        "SNAPPING": repr(app.get("snapping")),
        "POSITION_TRACKING": repr(app.get("position_tracking")),
        "TRACKING_FREQUENCY": repr(app.get("tracking_frequency")),
        "MAP_SKETCHING": repr(app.get("map_sketching")),
        "SKETCH_COLORS": repr(app.get("sketch_colors")),
        "PHOTO_SKETCHING": repr(app.get("photo_sketching")),
        "LAYER_ORDER": repr(app.get("layer_order")),
        "SELECTIVE_SYNC": repr(app.get("selective_sync")),
        "SELECTIVE_SYNC_FOLDER": repr(app.get("selective_sync_folder", "photos")),
        "FILTERS": py(app.get("filters") or []),
        "LOOKUP_LISTS": py(spec.get("lookup_lists", {})),
        "LAYERS": py(spec.get("layers", [])),
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
