# Workshop agent · Mergin Maps project builder

A Claude skill that designs a Mergin Maps survey project with you, then writes a
**commented PyQGIS script** you run inside QGIS to build it. Claude never
touches QGIS directly: you see and run every step.

## Use it

In this repo, ask Claude Code something like:

> Build me a Mergin Maps project to survey street trees in Sacramento.

Or call it by name: `/mergin-project-builder`. The skill is linked from
`.claude/skills/mergin-project-builder` (local only, `.claude/` is git-ignored).

Elsewhere, load the folder as a plugin:

```bash
claude --plugin-dir "/Users/vmstar/Dev/FOSS4G NA 2026/workshop-agent"
```

What happens:
1. It asks your QGIS version, and asks you to describe the project in your own
   words. An example prompt shows what to write: layers, fields, pick lists,
   CRS, and rules like "if dip is over 90, show 'Dip must be 0–90°'".
2. It asks about anything missing or unclear.
3. It checks the design against **confirmed Mergin Maps bugs**: open GitHub
   issues labelled `bug` in the mobile app and QGIS plugin. It goes through the
   ones that touch your features and avoids them or warns you.
4. It fills in defaults and tells you which: EPSG:4326, Mergin Maps background,
   High photo quality, who/when fields, spare fields.
5. It shows a summary to confirm.
6. It writes `build_<project>.py`. You run it in QGIS (Python Console > Show
   Editor > Open > Run).

## New or existing project

- **New** (`"mode": "new"`, default): run the script in an empty QGIS window;
  it creates the project folder.
- **Existing** (`"mode": "add"`): open your Mergin Maps project in QGIS, then
  run the script. It only adds new GeoPackages and layers. Existing layers,
  data, CRS, background and settings are left alone, and it stops before
  writing anything if a name already exists. The `.qgz` is backed up to
  `~/MerginMaps backups/` first. If anything fails halfway, the run removes
  what it created. Then sync with the plugin.

## Safety

The agent may only write its spec and script into one agreed output folder
(default `mergin-builds/<project>/`). It never edits other files, never opens
or changes your projects or GeoPackages itself, and never handles passwords or
syncs. GitHub issue text and project contents are treated as untrusted data.
The scripts enforce part of this:

- `render.py` rejects unsafe values (`..` paths, odd names, bad CRS) and won't
  overwrite without `--force`.
- `run_in_qgis.py` only builds inside the temp folder.
- The build script checks everything (names, types, expressions) before
  writing the first file, and undoes its own changes if something fails.

Full rules: "Safety rules" in `SKILL.md`.

## What's inside

```
workshop-agent/
├── .claude-plugin/plugin.json
├── skills/mergin-project-builder/
│   ├── SKILL.md                  # how the agent works (interview, defaults, spec)
│   ├── references/guidelines.md  # every rule, with its source
│   ├── templates/build_project.py# the commented script (SECTION 1 = settings)
│   ├── templates/check_project.py# checks any open project against the rules
│   └── scripts/
│       ├── render.py             # spec JSON -> build script (validates the spec)
│       ├── known_bugs.py         # confirmed GitHub bugs relevant to a spec
│       └── run_in_qgis.py        # test a build script in QGIS without a window
└── examples/
    ├── sierra-foothills-geology.json      # constraints, photo gallery
    ├── build_sierra_foothills_geology.py
    ├── sacramento-street-trees.json
    └── build_sacramento_street_trees.py   # ready to run
```

## What a generated project follows

- one GeoPackage per layer, all in the project folder; relative paths
- `uuid` on every layer, plus created/updated at/by, GPS accuracy on points
- hidden spare fields, so adding a question later needs no schema change
- dropdowns (fixed lists) and lookup lists (UUID-keyed, editable in the app)
- photos: relative paths, `photos/` folder, unique names, High quality
- one photo per feature (a photo field) or a **gallery** (`multiple_photos`):
  a `<layer>_photos.gpkg` table linked to the layer's `uuid`, as in the docs
- rules with your own messages (hard = can't save, soft = warning)
- the whole **Mergin Maps tab**: photo quality, snapping, position tracking,
  map and photo sketching, layer order, filters, selective sync. Tracking and
  sketch layers are built with the plugin's own recipe. In "add" mode a spec can
  change only these settings on an existing project.
- workarounds for known bugs (hidden fid, min/max on numbers, …)
- project extent, layer order, read-only background, one `.qgz`

Sources: your best-practices post (Sep 16, 2026), the Mergin Maps docs, and
the QGIS plugin and mobile app code. See `references/guidelines.md`.

## Tested

QGIS 3.42.1 on macOS, run without a window: build, then checker gives
`0 to fix`. The checker catches absolute paths, non-GeoPackage editable layers,
bad field names, fid-keyed lookups and absolute photo paths. **Not yet
tested:** QGIS 4 (the code uses QGIS 4–compatible names) and the real phone
round trip.

## Not generated yet

Other 1-N relations (e.g. repeat inspections), drill-down lists,
conditional visibility and tabs, offline basemaps. The agent explains the manual QGIS steps.
