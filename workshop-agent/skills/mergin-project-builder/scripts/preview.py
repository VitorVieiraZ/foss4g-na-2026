"""Compact preview of a spec: each layer's form as surveyors will see it.

Usage: python3 preview.py spec.json

Prints a short monospace block (paste it inside ``` in chat). One line per
visible field, in form order:

    label (* = required)   field name   type   input
        = default value          (when the app fills it in)
        ✓ "message" shown unless the rule holds (blocks saving or warning only)

Hidden automatic fields are summed up in one line per layer.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import app_settings, default_alias  # same rules as the script  # noqa: E402

TYPE = {"text": "text", "integer": "integer", "decimal": "decimal", "date": "date",
        "datetime": "date+time", "boolean": "yes/no"}
QUALITY = {0: "original", 1: "high", 2: "medium", 3: "low"}
SNAP = {0: "off", 1: "basic", 2: "follow QGIS"}
FREQ = {0: "best", 1: "normal", 2: "low"}


def short(items, limit=4):
    items = [str(i) for i in items]
    return " · ".join(items[:limit]) + (f" · +{len(items) - limit}" if len(items) > limit else "")


def lean(expression, limit=70):
    """Shorter rule text: drop the usual 'X IS NULL OR (...)' guard."""
    import re
    m = re.match(r'^\s*(\S+) IS NULL OR \(?(.*?)\)?\s*$', expression)
    text = f"{m.group(2)}  (empty is ok)" if m else expression
    return text if len(text) <= limit else text[:limit - 1] + "…"


def number_range(f):
    lo, hi = f.get("min"), f.get("max")
    if lo is None and hi is None:
        return "number"
    return f"number {'' if lo is None else lo}–{'' if hi is None else hi}"


def input_of(f, lists):
    w = f.get("widget", "text")
    if w == "dropdown":
        return "pick: " + short(f.get("choices", []))
    if w == "lookup":
        values = lists.get(f.get("list"), [])
        many = "pick many" if f.get("multiple") else "pick"
        return f"{many} from {f.get('list')} ({len(values)}, editable)"
    if w == "number":
        return number_range(f)
    return {"text": "typed", "notes": "typed, multi-line", "checkbox": "switch",
            "date": "calendar", "photo": "photo (camera/gallery)"}.get(w, w)


def form_order(fields):
    """Fields in the order the form shows them: by tab (first use), then
    each group kept together, as form_layout() in build_project.py does."""
    tabs = {}
    for f in fields:
        tabs.setdefault(f.get("tab"), []).append(f)
    ordered = []
    for tab_fields in tabs.values():
        slots = {}
        for f in tab_fields:
            key = f.get("group") or ("", f["name"])
            slots.setdefault(key, []).append(f)
        for slot in slots.values():
            ordered.extend(slot)
    return ordered


def layer_block(layer, lists, out):
    fields = layer.get("fields", [])
    visible = [f for f in fields if f.get("widget", "text") != "hidden"]
    hidden = [f for f in fields if f.get("widget", "text") == "hidden"]
    title = next((f.get("alias") or default_alias(f) for f in fields if f["name"] == layer.get("title")), None)
    head = [layer["name"].upper(), layer["geometry"]]
    if title:
        head.append(f"title: {title}")
    if layer.get("multiple_photos"):
        head.append("photo gallery")
    out.append("  ".join([head[0]] + [" · ".join(head[1:])]))

    rows = []
    for f in form_order(visible):
        label = (f.get("alias") or default_alias(f)) + (" *" if f.get("required") else "")
        rows.append((label, f["name"], TYPE.get(f["type"], f["type"]), input_of(f, lists), f))
    w = [max([len(r[i]) for r in rows] + [0]) for i in range(3)]
    where = (None, None)
    for label, name, kind, how, f in rows:
        if (f.get("tab"), f.get("group")) != where:
            if f.get("tab") and f.get("tab") != where[0]:
                out.append(f"  [ {f['tab']} ]")
            if f.get("group"):
                out.append(f"  ── {f['group']}")
            where = (f.get("tab"), f.get("group"))
        out.append(f"  {label:<{w[0]}}  {name:<{w[1]}}  {kind:<{w[2]}}  {how}")
        pad = " " * (w[0] + 4)
        if f.get("default"):
            again = ", on every edit" if f.get("update") else ""
            out.append(f"{pad}= {f['default']}{again}")
        rule = f.get("constraint")
        if rule:
            strength = "blocks saving" if rule.get("hard", True) else "warning only"
            out.append(f"{pad}✓ \"{rule.get('message', '')}\"  {strength}")
            out.append(f"{pad}  unless: {lean(rule['expression'])}")

    auto = ["uuid", "created/updated at·by"] + (["GPS accuracy"] if layer["geometry"] == "point" else [])
    extra = [f["name"] for f in hidden]
    line = "  ┄ hidden, filled by the app: " + " · ".join(auto) + " · 5 spare fields"
    if extra:
        line += " · also hidden: " + ", ".join(extra)
    out.append(line)
    if layer.get("multiple_photos"):
        out.append(f"  ┄ {layer['name']}_photos: Photo · Caption, one row per photo, linked by uuid")
    out.append("")


def main(path):
    spec = json.load(open(path, encoding="utf-8"))
    lists = spec.get("lookup_lists", {})
    app = app_settings(spec)
    out = []

    mode = spec.get("mode", "new")
    bg = {"mergin": "Mergin Maps tiles", "osm": "OpenStreetMap", None: "no background"}.get(
        spec.get("background", "mergin"), spec.get("background"))
    where = (spec.get("area_of_interest") or {}).get("label")
    project = [spec["project_name"], "new project" if mode == "new" else "add to existing"]
    if mode == "new":
        project.append(spec.get("crs", "EPSG:4326"))
    elif spec.get("layers"):
        project.append(f"new layers in {spec.get('crs', 'EPSG:4326')}")
    if spec.get("qgis_version"):
        project.append(f"QGIS {spec['qgis_version']}")
    if mode == "new":
        project += [bg] + ([where] if where else [])
    out.append("PROJECT  " + " · ".join(project))

    settings = []
    if "photo_quality" in app or mode == "new":
        settings.append(f"photos {QUALITY.get(app.get('photo_quality', 1))}")
    if "snapping" in app or mode == "new":
        settings.append(f"snapping {SNAP.get(app.get('snapping', 0))}")
    if app.get("position_tracking"):
        settings.append(f"tracking {FREQ.get(app.get('tracking_frequency', 1), 'normal')}")
    sketch = [n for k, n in (("map_sketching", "map"), ("photo_sketching", "photo")) if app.get(k)]
    if sketch:
        settings.append("sketching " + "+".join(sketch))
    if app.get("layer_order") == "alphabetical":
        settings.append("layers A–Z")
    if app.get("selective_sync"):
        settings.append(f"selective sync {app.get('selective_sync_folder', 'photos')}/")
    if app.get("filters"):
        names = [f.get("name") or f"{f['layer']}.{f['field']}" for f in app["filters"]]
        settings.append("filters: " + ", ".join(names))
    if settings:
        out.append("APP      " + " · ".join(settings))
    for name, values in lists.items():
        out.append(f"LIST     {name} ({len(values)}): {short(values)}")
    out.append("")

    for layer in spec.get("layers", []):
        layer_block(layer, lists, out)
    if not spec.get("layers"):
        out.append("(no new layers: only the settings above change)")
    out.append("* required · = filled in automatically · ✓ message shown in the app")
    print("\n".join(out).rstrip())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 preview.py spec.json")
    main(sys.argv[1])
