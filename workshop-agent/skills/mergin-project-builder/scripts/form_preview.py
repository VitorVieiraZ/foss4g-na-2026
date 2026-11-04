"""Interactive form preview: one HTML page that looks like the Mergin Maps app.

Usage: python3 form_preview.py spec.json output.html [--force]

Writes a single self-contained page (no internet needed): a phone showing
each layer's form with the app's own colours, fonts and icons, including
tabs, groups, pick lists, photos and the rules with their messages.
People can fill it in, try the rules and save, to check the form before
anything is built in QGIS. Nothing is sent anywhere.

The page follows the same tab/group rules as form_layout() in
templates/build_project.py, so what you see is what the script builds.
"""
import base64
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import check_settings, check_spec, fill_aliases  # same checks as the script  # noqa: E402

ASSETS = os.path.join(HERE, "..", "assets", "form-preview")


def icons():
    """The app's SVG icons, recoloured with currentColor (the app tints them too)."""
    out = {}
    folder = os.path.join(ASSETS, "icons")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".svg"):
            svg = open(os.path.join(folder, name), encoding="utf-8").read()
            svg = re.sub(r'(stroke|fill)="(?!none)[^"]*"', r'\1="currentColor"', svg)
            out[name[:-4]] = svg
    return out


def script_json(value):
    """JSON safe inside a <script> tag."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def main(spec_path, out_path, force=False):
    spec = json.load(open(spec_path, encoding="utf-8"))
    check_settings(spec)
    check_spec(spec)
    fill_aliases(spec)
    target = os.path.realpath(out_path)
    if not target.endswith(".html"):
        sys.exit("form_preview.py: the output must be a .html file")
    if target.startswith(os.path.realpath(os.path.join(HERE, "..")) + os.sep):
        sys.exit("form_preview.py: don't write into the skill's own folder")
    if os.path.exists(target) and not force:
        sys.exit(f"form_preview.py: {out_path} exists. Pass --force to replace it.")
    font = base64.b64encode(open(os.path.join(ASSETS, "inter-latin.woff2"), "rb").read()).decode()
    page = open(os.path.join(ASSETS, "app.html"), encoding="utf-8").read()
    values = {"FONT": font, "SPEC": script_json(spec), "ICONS": script_json(icons())}
    # One pass over the template only, so text inside the spec is never expanded.
    page = re.sub(r"\{\{([A-Z]+)\}\}", lambda m: values[m.group(1)], page)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as out:
        out.write(page)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 2:
        sys.exit("Usage: python3 form_preview.py spec.json output.html [--force]")
    main(args[0], args[1], force="--force" in sys.argv)
