"""Find confirmed Mergin Maps bugs that touch the features a project uses.

Usage:
    python3 known_bugs.py spec.json [--all]     # bugs relevant to this spec
    python3 known_bugs.py --show mobile#4758   # read one issue in full

"Confirmed" = open GitHub issue labelled "bug" in MerginMaps/mobile or
MerginMaps/qgis-plugin, and NOT labelled as unconfirmed (not reproducible,
needs more info, duplicate, invalid, only in an unreleased version).

Uses the public GitHub API without a login (60 requests/hour). Results are
cached for a day in known_bugs_cache.json next to this script.
"""
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "known_bugs_cache.json")
REPOS = ["mobile", "qgis-plugin"]
UNCONFIRMED = {
    "not-reproducible", "needs-more-info", "can't reproduce", "duplicate",
    "invalid", "wontfix", "bug in not released version", "stale", "question",
    "support question",
}

# Project feature -> words that show up in related bug titles/labels.
FEATURES = {
    "photos": ["photo", "camera", "image", "picture", "attachment", "gallery", "exif"],
    "pick lists (Value Map)": ["value map", "valuemap", "dropdown", "combobox"],
    "lookup lists (Value Relation)": ["value relation", "valuerelation"],
    "constraints": ["constraint", "required field", "not null", "validation message"],
    "default values": ["default value", "@mm_", "@position", "apply on update"],
    "dates": ["date", "calendar", "time zone", "timezone"],
    "checkboxes": ["checkbox", "boolean"],
    "numbers": ["range", "slider", "spinbox", "decimal", "number"],
    "forms": ["form"],
    "relations": ["relation"],
    "GPS": ["gps", "gnss", "position", "accuracy", "bluetooth"],
    "sync": ["sync", "geodiff", "conflict"],
    "lines and polygons": ["polygon", "line", "vertex", "geometry", "snapping"],
    "background maps": ["vector tile", "basemap", "background", "mbtiles", "xyz"],
    "QGIS 4": ["qgis 4", "qgis4", "qt6", "qt 6"],
}


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "mergin-project-builder"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def confirmed_bugs():
    if os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < 86400:
        return json.load(open(CACHE))
    bugs = []
    for repo in REPOS:
        for page in range(1, 6):
            items = get(f"https://api.github.com/repos/MerginMaps/{repo}/issues"
                        f"?labels=bug&state=open&per_page=100&page={page}")
            for i in items:
                labels = [l["name"] for l in i["labels"]]
                if "pull_request" in i or UNCONFIRMED & {l.lower() for l in labels}:
                    continue
                bugs.append({"id": f"{repo}#{i['number']}", "title": i["title"],
                             "labels": labels, "url": i["html_url"], "updated": i["updated_at"][:10]})
            if len(items) < 100:
                break
    json.dump(bugs, open(CACHE, "w"), indent=1)
    return bugs


def features_in(spec):
    """Which FEATURES keys a spec uses."""
    used = {"forms", "sync", "default values"}  # every generated project has these
    widgets = {f.get("widget", "text") for l in spec["layers"] for f in l["fields"]}
    geoms = {l["geometry"] for l in spec["layers"]}
    if "photo" in widgets: used.add("photos")
    if any(l.get("multiple_photos") for l in spec["layers"]):
        used |= {"photos", "relations"}
    if "dropdown" in widgets: used.add("pick lists (Value Map)")
    if "lookup" in widgets: used.add("lookup lists (Value Relation)")
    if "date" in widgets: used.add("dates")
    if "checkbox" in widgets: used.add("checkboxes")
    if "number" in widgets: used.add("numbers")
    if any(f.get("constraint") or f.get("required") for l in spec["layers"] for f in l["fields"]):
        used.add("constraints")
    if "point" in geoms: used.add("GPS")
    if geoms & {"line", "polygon"}: used.add("lines and polygons")
    if spec.get("background"): used.add("background maps")
    if str(spec.get("qgis_version", "")).startswith("4"): used.add("QGIS 4")
    return used


def matches(bug, words):
    text = (bug["title"] + " " + " ".join(bug["labels"])).lower()
    return any(re.search(r"\b" + re.escape(w) + r"s?\b", text) for w in words)


SEVERE = {"data corruption - sync failure - crash - anr", "blocker", "critical",
          "high priority", "regression"}
LIMIT = 8  # per feature; the agent can ask for more with --all


def severity(bug):
    return 1 if SEVERE & {l.lower() for l in bug["labels"]} else 0


def main():
    if sys.argv[1:2] == ["--show"]:
        repo, num = sys.argv[2].split("#")
        i = get(f"https://api.github.com/repos/MerginMaps/{repo}/issues/{num}")
        print(f"{i['title']}\n{i['html_url']}\nlabels: {[l['name'] for l in i['labels']]}\n")
        print((i.get("body") or "")[:4000])
        return
    spec = json.load(open(sys.argv[1]))
    bugs = confirmed_bugs()
    used = sorted(features_in(spec))
    print(f"{len(bugs)} confirmed open bugs. Features in this project: {', '.join(used)}\n")
    for feature in used:
        hits = [b for b in bugs if matches(b, FEATURES[feature])]
        if not hits:
            continue
        hits.sort(key=lambda b: (severity(b), b["updated"]), reverse=True)
        shown = hits if "--all" in sys.argv else hits[:LIMIT]
        print(f"## {feature} ({len(hits)})")
        for b in shown:
            flag = "!!" if severity(b) else "  "
            print(f"{flag} {b['id']:<18} {b['title'][:90]}  [{', '.join(b['labels'])}]")
        if len(shown) < len(hits):
            print(f"   ... {len(hits) - len(shown)} more (use --all)")
        print()
    print("!! = crash, data loss, regression or high priority. Read one: --show mobile#1234")


if __name__ == "__main__":
    main()
