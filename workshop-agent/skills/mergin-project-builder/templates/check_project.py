"""
===============================================================================
  MERGIN MAPS PROJECT CHECKER
===============================================================================

Checks the project that is OPEN in QGIS against the Mergin Maps guidelines,
before you upload it or hand it to your field team. It changes nothing.

How to run it
-------------
  1. Open your project in QGIS.
  2. Plugins > Python Console > Show Editor, open this file, press Run.
  3. Read the report: [OK] passed, [!!] must fix, [??] worth a look.

The checks follow the Mergin Maps docs (https://merginmaps.com/docs) and the
warnings the Mergin Maps QGIS plugin shows when you sync.
===============================================================================
"""

import os
import re

from qgis.core import Qgis, QgsExpression, QgsMapLayer, QgsProject, QgsVectorDataProvider

# QGIS 4 names first, QGIS 3 names as a fallback.
VECTOR = Qgis.LayerType.Vector if hasattr(Qgis, "LayerType") else QgsMapLayer.VectorLayer
_caps = getattr(Qgis, "VectorProviderCapability", None) or getattr(QgsVectorDataProvider, "Capability", QgsVectorDataProvider)
ADD_FEATURES, CHANGE_VALUES = _caps.AddFeatures, _caps.ChangeAttributeValues

project = QgsProject.instance()
folder = project.homePath()
problems, notes, passed = [], [], []


def must_fix(msg):
    problems.append(msg)


def look_at(msg):
    notes.append(msg)


def inside_project(path):
    """True if path is inside the project folder."""
    path = os.path.realpath(path)
    try:
        return os.path.commonpath([path, os.path.realpath(folder)]) == os.path.realpath(folder)
    except ValueError:  # different drives on Windows
        return False


if not project.fileName():
    raise RuntimeError("Open (or save) your project first, then run the checker again.")

# 1 · Exactly one QGIS project file in the folder ------------------------------
project_files = [os.path.join(d, f) for d, _, files in os.walk(folder) for f in files
                 if f.lower().endswith((".qgs", ".qgz")) and ".mergin" not in os.path.relpath(d, folder).split(os.sep)]
if len(project_files) > 1:
    must_fix("More than one .qgs/.qgz file in the project folder: keep only one.")
else:
    passed.append("One QGIS project file")

# 2 · Relative paths, no preset home path --------------------------------------
absolute, _ = project.readEntry("Paths", "/Absolute", "false")
if absolute.lower() != "false":
    must_fix("Paths are absolute. Project > Properties > General > Save paths: Relative.")
else:
    passed.append("Relative paths")
if project.presetHomePath():
    must_fix("A project home path is set. Clear it in Project > Properties > General.")

# 3 · Layers -------------------------------------------------------------------
gpkg_layers = {}
editable = 0
for layer in project.mapLayers().values():
    name = layer.name()
    source = layer.source().split("|")[0]
    provider = layer.providerType()

    # Files must live inside the project folder (only that folder syncs).
    if provider in ("ogr", "gdal") and os.path.exists(source) and not inside_project(source):
        must_fix(f"'{name}' is outside the project folder: {source}")

    if layer.type() != VECTOR:
        continue
    dp = layer.dataProvider()
    caps = dp.capabilities()
    can_edit = bool(caps & ADD_FEATURES) or bool(caps & CHANGE_VALUES)
    if can_edit and not layer.readOnly():
        editable += 1
        if dp.storageType() != "GPKG":
            must_fix(f"'{name}' is editable but not a GeoPackage ({dp.storageType()}). "
                     "Edits in other formats cannot be merged.")
    if dp.storageType() == "GPKG":
        gpkg_layers.setdefault(os.path.realpath(source), []).append(name)

    fields = layer.fields()
    names = [f.name() for f in fields]

    # Field names the plugin rejects.
    for f in names:
        if re.search(r'[\\/()\[\]{}"\n\r]', f):
            must_fix(f"'{name}': field name '{f}' has characters Mergin Maps rejects.")

    # A UUID field for stable IDs.
    if can_edit and not any(fields.field(i).name().lower() in ("uuid", "unique_id", "unique-id")
                            for i in range(fields.count())):
        look_at(f"'{name}' has no uuid field. Add one (default uuid()) if anything links to it.")

    for i in range(fields.count()):
        # Expressions that don't parse break forms in the app.
        constraint = fields.field(i).constraints().constraintExpression()
        default = layer.defaultValueDefinition(i).expression()
        for kind, text in (("rule", constraint), ("default value", default)):
            if text and QgsExpression(text).hasParserError():
                must_fix(f"'{name}.{names[i]}': the {kind} expression is not valid: "
                         f"{QgsExpression(text).parserErrorString()}")
        setup = layer.editorWidgetSetup(i)
        kind, cfg = setup.type(), setup.config()

        # Photos: relative paths, folder set by expression.
        if kind == "ExternalResource":
            root = (cfg.get("PropertyCollection") or {}).get("properties", {}).get("propertyRootPath", {})
            root_active = bool(root.get("active"))
            if cfg.get("RelativeStorage", 0) == 0 and not root_active:
                must_fix(f"'{name}.{names[i]}': photo paths are absolute. Store them relative to the project.")
            if root_active and root.get("type") == 3 and not re.search(
                    r"@project_(home|path|folder)", root.get("expression", "")):
                must_fix(f"'{name}.{names[i]}': photo folder expression should start from @project_home.")
            if not root_active and cfg.get("DefaultRoot"):
                look_at(f"'{name}.{names[i]}': use a data-defined default path "
                        "(@project_home + '/photos') instead of a fixed folder.")

        # Lookups must not key on fid.
        if kind == "ValueRelation":
            if not cfg.get("Layer") or not cfg.get("Key"):
                must_fix(f"'{name}.{names[i]}': Value Relation is missing its layer or key.")
            elif cfg.get("Key") == "fid":
                must_fix(f"'{name}.{names[i]}': Value Relation uses fid as key. Use a uuid field.")

# One layer per GeoPackage.
for path, layers in gpkg_layers.items():
    if len(set(layers)) > 1:
        look_at(f"{os.path.basename(path)} holds several layers ({', '.join(sorted(set(layers)))}). "
                "Mergin Maps recommends one GeoPackage per layer.")
if editable == 0:
    must_fix("No editable layer: surveyors would have nothing to capture.")
else:
    passed.append(f"{editable} editable layer(s)")

# Relations must not use fid.
for rel in project.relationManager().relations().values():
    for child_field, parent_field in rel.fieldPairs().items():
        if "fid" in (child_field, parent_field):
            must_fix(f"Relation '{rel.name()}' links on fid. Link on a uuid field instead.")

# 4 · Mergin Maps app settings -------------------------------------------------
quality, ok = project.readNumEntry("Mergin", "PhotoQuality", 0)
if quality == 0:
    look_at("Photo quality is 'Original': phone photos can be 10 MB+. Consider High "
            "(Project > Properties > Mergin Maps).")
sort_method, ok = project.readNumEntry("Mergin", "SortLayersMethod/Method", 1)
if not ok:
    look_at("Layer order in the app is alphabetical. Set 'QGIS layer order' in the Mergin Maps tab.")
if project.viewSettings().presetFullExtent().isEmpty():
    look_at("No project extent: 'Zoom to project' in the app will zoom to all layers.")

# 5 · File names the server refuses --------------------------------------------
for d, _, files in os.walk(folder):
    for f in files:
        if re.search(r'[\x00-\x19<>:|?*"]', f):
            must_fix(f"File name not allowed by Mergin Maps: {os.path.join(d, f)}")

# Report -----------------------------------------------------------------------
print(f"\nChecked: {project.fileName()}\n")
for p in passed:
    print(f"  [OK] {p}")
for p in problems:
    print(f"  [!!] {p}")
for n in notes:
    print(f"  [??] {n}")
print(f"\n{len(problems)} to fix, {len(notes)} to look at.")
