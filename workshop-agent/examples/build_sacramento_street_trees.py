"""
===============================================================================
  MERGIN MAPS PROJECT BUILDER  ·  Sacramento street trees
===============================================================================

What this script does
---------------------
It builds a ready-to-sync Mergin Maps project folder on your computer:

    sacramento-street-trees/
    ├── sacramento-street-trees.qgz      <- the QGIS project (relative paths)
    ├── <one .gpkg per layer>     <- every survey layer in its own GeoPackage
    └── photos/                   <- where photos taken in the field are saved

It follows the Mergin Maps guidelines (https://merginmaps.com/docs):
  * one GeoPackage per layer, all inside the project folder
  * relative paths, so the project opens on any computer or phone
  * a UUID field on every layer (stable IDs that survive sync)
  * "who / when" fields filled in automatically by the app
  * spare hidden fields, so you can add questions later without
    changing the data structure (structure changes can break sync)

How to run it
-------------
  1. Open QGIS (a new, empty project is best).
  2. Plugins > Python Console, then click "Show Editor" (the notepad icon).
  3. Open this file in the editor and press "Run Script" (the green arrow).
  4. Read the summary printed at the end. It tells you what to do next.

Where to change things
----------------------
Everything you are likely to change is in SECTION 1 (SETTINGS) just below.
You should not need to touch SECTION 2 or 3. They are commented, so you can
follow along if you are curious.

Made for: QGIS 3.42  (tested with QGIS 3.28 or newer, and QGIS 4)
Generated on: 2026-11-02
===============================================================================
"""

import json
import os
import re
import shutil
import time

# =============================================================================
# SECTION 1 · SETTINGS  (edit here)
# =============================================================================

# --- New project, or add to one you already have? ----------------------------
#   "new" -> create a new project folder (start QGIS with an empty project)
#   "add" -> add these layers to the project OPEN in QGIS right now, e.g. one
#            you downloaded with the Mergin Maps plugin. Existing layers,
#            data and settings are never changed; only new .gpkg files are added.
MODE = "new"

# --- Where to create the project ("new" mode only) ---------------------------
# The project folder is created INSIDE this folder. Use a local drive:
# network drives are not supported by Mergin Maps.
# os.path.expanduser("~") is your home folder (works on Windows, macOS and Linux).
PARENT_FOLDER = os.path.join(os.path.expanduser("~"), "MerginMaps Projects")

# Name of the project folder and the .qgz file. Use letters, numbers, "-" or "_".
# Tip: you choose the Mergin Maps project name when you upload it, and that
# name cannot be changed later, so pick it carefully.
PROJECT_NAME = "sacramento-street-trees"
# Title shown in QGIS (Project > Properties).
TITLE = "Sacramento street trees"

# --- Coordinate reference system ---------------------------------------------
# Used for the project and for the new layers.
# EPSG:4326 (WGS 84, latitude/longitude) is the default: it is what GPS uses.
# For accurate lengths and areas, use a local projected CRS instead,
# e.g. "EPSG:26910" (UTM zone 10N, northern California).
CRS = "EPSG:4326"

# --- Area of interest (optional) ---------------------------------------------
# The "Zoom to project" button in the app zooms here.
# Longitude/latitude box: [west, south, east, north]. Set to None to skip.
AREA_OF_INTEREST = [-121.56, 38.43, -121.36, 38.69]  # Sacramento, CA

# --- Background map ----------------------------------------------------------
#   "mergin" -> Mergin Maps vector tiles (OpenStreetMap data, online,
#               free for Mergin Maps users, light on mobile data)
#   "osm"    -> standard OpenStreetMap raster tiles (online)
#   None     -> no background map
BACKGROUND = "mergin"

# --- Mergin Maps tab (Project > Properties > Mergin Maps) --------------------
# The same options as that tab. None = "new": the plugin's default,
#                                       "add": leave the project's setting as it is.
#
# Photo size saved by the app: 0 = original, 1 = high, 2 = medium, 3 = low
PHOTO_QUALITY = 1
# Snapping in the app: 0 = none, 1 = basic (vertices and segments),
# 2 = follow the QGIS snapping settings (the script turns QGIS snapping on)
SNAPPING = 0
# Position tracking: records the surveyor's route as lines in tracking_layer.gpkg
POSITION_TRACKING = None
# How often a position is recorded: 0 = best (often), 1 = normal, 2 = low
TRACKING_FREQUENCY = None
# Map sketching: draw freehand notes on the map (saved in map_sketches.gpkg)
MAP_SKETCHING = None
# Colours offered for sketches (up to 7, hex)
SKETCH_COLORS = None
# Photo sketching: draw on photos after taking them
PHOTO_SKETCHING = None
# Layer order in the app: "qgis" (as in the Layers panel) or "alphabetical"
LAYER_ORDER = None
# Selective sync: other devices don't download each other's files in this
# folder (e.g. photos). Saves mobile data; photos stay on the server.
SELECTIVE_SYNC = None
SELECTIVE_SYNC_FOLDER = 'photos'
# Filters: let surveyors filter features in the app, e.g. "only Poor trees".
#   {"layer": "trees", "field": "condition", "name": "Condition"}
#   "type" is worked out from the field (dropdown -> "Single select",
#   checkbox -> "Checkbox", number -> "Number", date -> "Date", text -> "Text").
# In "add" mode, filters can also use layers already in the project.
FILTERS = [   {'layer': 'trees', 'field': 'condition', 'name': 'Condition'},
    {'layer': 'trees', 'field': 'needs_pruning', 'name': 'Needs pruning'}]

# Folder (inside the project) where photos are saved
PHOTO_FOLDER = "photos"
# How photos are named (a QGIS expression; ".jpg" is added by the app).
# Default: layer name, surveyor, date and time -> trees-sarah-261102143005.jpg
PHOTO_NAME = "@layer_name + '-' + @mm_username + '-' + format_date(now(), 'yyMMddhhmmss')"

# --- Fields added to every layer automatically -------------------------------
# uuid        : unique ID created once per feature (never edit it).
#               Use it to link tables, NOT the "fid" column, which can change
#               when people sync at the same time.
# created_*/updated_* : who and when, filled in by the app.
ADD_TRACKING_FIELDS = True
# Hidden spare fields (text, whole number, decimal, date). Later, if you need
# a new question, give a spare field an alias and show it in the form.
ADD_SPARE_FIELDS = True

# --- Lookup lists (optional) -------------------------------------------------
# A lookup list is a small table that feeds a drop-down. Unlike a "dropdown"
# field, people can add new values to it in the field (from the app).
# Each list becomes its own GeoPackage, like every other layer.
LOOKUP_LISTS = {   'tree_species': [   'Valley oak',
                        'London plane',
                        'Chinese pistache',
                        'Crape myrtle',
                        'Coast redwood',
                        'Unknown']}

# --- Survey layers -----------------------------------------------------------
# One entry per layer. Each layer is saved as <name>.gpkg in the project folder.
#
#   "geometry": "point", "line", "polygon" or "none" (a table without a map)
#   "title":    field shown as the feature's title in the app
#   "color":    map colour (hex)
#   "multiple_photos": True -> several photos per feature (a gallery).
#              Creates a separate table <name>_photos.gpkg, linked to this
#              layer by its uuid (as in the Mergin Maps docs, "Attaching
#              multiple photos to one feature"). Don't also add a single
#              "photo" field to the same layer: the app can mix them up
#              (github.com/MerginMaps/mobile/issues/2029).
#
# Each field:
#   "name"     column name: lowercase, no spaces, never rename it later
#              (change the "alias" instead)
#   "type"     "text", "integer", "decimal", "date", "datetime" or "boolean"
#   "alias"    the label people see in the form
#   "widget"   how the field is filled in:
#              "text"      free text, one line
#              "notes"     free text, several lines
#              "dropdown"  pick one of "choices" (fixed list)
#              "lookup"    pick from a LOOKUP_LISTS table ("list": its name,
#                          "multiple": True to allow several)
#              "number"    number box ("min"/"max" optional)
#              "checkbox"  yes / no
#              "date"      calendar (date or date + time)
#              "photo"     take a photo or pick one from the gallery
#                          ("photo_name": optional naming expression)
#              "hidden"    not shown in the form
#   "required" True = the form cannot be saved while it is empty
#   "default"  a QGIS expression filled in automatically, e.g. "now()"
#   "constraint" a rule with a message shown in the app when it is broken:
#              {"expression": '"dip" <= 90', "message": "Dip must be 0-90°",
#               "hard": True}   (hard = cannot save, False = warning only)
LAYERS = [   {   'name': 'trees',
        'geometry': 'point',
        'title': 'species',
        'color': '#1db278',
        'fields': [   {   'name': 'species',
                          'type': 'text',
                          'alias': 'Species',
                          'widget': 'lookup',
                          'list': 'tree_species',
                          'required': True},
                      {   'name': 'condition',
                          'type': 'text',
                          'alias': 'Condition',
                          'widget': 'dropdown',
                          'choices': ['Good', 'Fair', 'Poor', 'Dead'],
                          'required': True},
                      {   'name': 'height_m',
                          'type': 'decimal',
                          'alias': 'Height (m)',
                          'widget': 'number',
                          'min': 0,
                          'max': 80},
                      {   'name': 'needs_pruning',
                          'type': 'boolean',
                          'alias': 'Needs pruning?',
                          'widget': 'checkbox'},
                      {'name': 'photo', 'type': 'text', 'alias': 'Photo', 'widget': 'photo'},
                      {'name': 'notes', 'type': 'text', 'alias': 'Notes', 'widget': 'notes'}]},
    {   'name': 'sidewalk_damage',
        'geometry': 'line',
        'title': 'severity',
        'color': '#c2410c',
        'fields': [   {   'name': 'severity',
                          'type': 'text',
                          'alias': 'Severity',
                          'widget': 'dropdown',
                          'choices': ['Minor', 'Moderate', 'Severe'],
                          'required': True},
                      {   'name': 'inspected_on',
                          'type': 'date',
                          'alias': 'Inspected on',
                          'widget': 'date',
                          'default': 'now()'},
                      {'name': 'photo', 'type': 'text', 'alias': 'Photo', 'widget': 'photo'}]},
    {   'name': 'planting_sites',
        'geometry': 'polygon',
        'title': 'site_name',
        'color': '#f6a463',
        'fields': [   {   'name': 'site_name',
                          'type': 'text',
                          'alias': 'Site name',
                          'widget': 'text',
                          'required': True},
                      {   'name': 'trees_possible',
                          'type': 'integer',
                          'alias': 'Trees that fit',
                          'widget': 'number',
                          'min': 0,
                          'max': 500}]}]


# =============================================================================
# SECTION 2 · HELPERS  (you do not need to change anything below)
# =============================================================================

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDataSourceUri,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFieldConstraints,
    QgsFields,
    QgsMapLayer,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsReferencedRectangle,
    QgsRelation,
    QgsSymbol,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsVectorLayerUtils,
    QgsVectorTileLayer,
    QgsWkbTypes,
    QgsLineSymbol,
    QgsProperty,
    QgsSingleSymbolRenderer,
    QgsSymbolLayer,
    QgsAttributeEditorField,
    QgsEditFormConfig,
    QgsExpression,
)
from qgis.PyQt.QtGui import QColor

# QGIS 4 (Qt 6) moved some names around. These small helpers find the right
# name on both QGIS 3 and QGIS 4, so the same script runs on both.
try:
    from qgis.PyQt.QtCore import QMetaType

    _TYPES = {
        "text": QMetaType.Type.QString,
        "integer": QMetaType.Type.LongLong,
        "decimal": QMetaType.Type.Double,
        "date": QMetaType.Type.QDate,
        "datetime": QMetaType.Type.QDateTime,
        "boolean": QMetaType.Type.Bool,
    }
    QgsField("probe", _TYPES["text"])  # QGIS older than 3.38 rejects QMetaType
except Exception:
    from qgis.PyQt.QtCore import QVariant

    _TYPES = {
        "text": QVariant.String,
        "integer": QVariant.LongLong,
        "decimal": QVariant.Double,
        "date": QVariant.Date,
        "datetime": QVariant.DateTime,
        "boolean": QVariant.Bool,
    }


def _enum(owner, scoped, name):
    """Return owner.scoped.name (QGIS 4 style) or owner.name (QGIS 3 style)."""
    group = getattr(owner, scoped, None)
    if group is not None and hasattr(group, name):
        return getattr(group, name)
    return getattr(owner, name)


_WKB = Qgis.WkbType if hasattr(Qgis, "WkbType") else QgsWkbTypes  # QgsWkbTypes before 3.30
GEOMETRY = {"point": _WKB.Point, "line": _WKB.LineString,
            "polygon": _WKB.Polygon, "none": _WKB.NoGeometry}
NOT_NULL = _enum(QgsFieldConstraints, "Constraint", "ConstraintNotNull")
EXPRESSION = _enum(QgsFieldConstraints, "Constraint", "ConstraintExpression")
HARD = _enum(QgsFieldConstraints, "ConstraintStrength", "ConstraintStrengthHard")
SOFT = _enum(QgsFieldConstraints, "ConstraintStrength", "ConstraintStrengthSoft")
IDENTIFIABLE = _enum(QgsMapLayer, "LayerFlag", "Identifiable")
SEARCHABLE = _enum(QgsMapLayer, "LayerFlag", "Searchable")
WRITER_OK = _enum(QgsVectorFileWriter, "WriterError", "NoError")


# Everything this script creates is recorded here, so that if something goes
# wrong halfway, undo() can remove exactly that and nothing else.
CREATED_FILES = []    # .gpkg files and folders we created
ADDED_LAYER_IDS = []  # layers we added to the project


def add_layer(project, layer):
    """Add a layer to the project (not yet to the layer list) and remember it."""
    project.addMapLayer(layer, False)
    ADDED_LAYER_IDS.append(layer.id())


def undo(project):
    """Remove what this run added: new layers, new files. Nothing else."""
    if not CREATED_FILES and not ADDED_LAYER_IDS:
        return  # stopped before anything was created
    project.removeMapLayers(ADDED_LAYER_IDS)
    if MODE == "add" and project.fileName():
        project.read(project.fileName())  # back to the saved project file
    else:
        project.clear()  # "new" mode started from an empty project
    for path in reversed(CREATED_FILES):
        for p in (path, path + "-wal", path + "-shm"):
            if os.path.isfile(p):
                os.remove(p)
        if os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)  # only folders we created, and only if empty


def stop(message):
    """Stop the script with a clear message (what was created is removed again)."""
    raise RuntimeError("\n\n  STOPPED: " + message + "\n")


def tracking_fields():
    """The automatic who/when fields (Mergin Maps docs: Default Values)."""
    return [
        {"name": "uuid", "type": "text", "alias": "Unique ID", "widget": "hidden", "default": "uuid()"},
        {"name": "created_at", "type": "datetime", "alias": "Created at", "widget": "hidden", "default": "now()"},
        {"name": "created_by", "type": "text", "alias": "Created by", "widget": "hidden", "default": "@mm_username"},
        {"name": "updated_at", "type": "datetime", "alias": "Updated at", "widget": "hidden", "default": "now()", "update": True},
        {"name": "updated_by", "type": "text", "alias": "Updated by", "widget": "hidden", "default": "@mm_username", "update": True},
    ]


def spare_fields():
    """Hidden backup fields (Mergin Maps docs: QGIS Project Preparation)."""
    return [
        {"name": "spare_text_1", "type": "text", "widget": "hidden"},
        {"name": "spare_text_2", "type": "text", "widget": "hidden"},
        {"name": "spare_int_1", "type": "integer", "widget": "hidden"},
        {"name": "spare_real_1", "type": "decimal", "widget": "hidden"},
        {"name": "spare_date_1", "type": "date", "widget": "hidden"},
    ]


def create_geopackage(folder, name, geometry, fields, crs):
    """Create <folder>/<name>.gpkg holding ONE layer called <name>."""
    path = os.path.join(folder, name + ".gpkg")
    CREATED_FILES.append(path)
    qfields = QgsFields()
    for f in fields:
        qfields.append(QgsField(f["name"], _TYPES[f["type"]]))
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = name
    writer = QgsVectorFileWriter.create(
        path, qfields, GEOMETRY[geometry], crs,
        QgsProject.instance().transformContext(), options,
    )
    if writer.hasError() != WRITER_OK:
        stop(f"could not create {path}: {writer.errorMessage()}")
    del writer  # closing the writer finishes writing the file
    layer = QgsVectorLayer(f"{path}|layername={name}", name, "ogr")
    if not layer.isValid():
        stop(f"{path} was created but QGIS cannot open it")
    return layer


def setup_field(layer, field, lookup_layers):
    """Set the alias, form widget, default value and constraint of one field."""
    idx = layer.fields().indexOf(field["name"])
    widget = field.get("widget", "text")

    if field.get("alias"):
        layer.setFieldAlias(idx, field["alias"])

    # --- form widget ---
    if widget == "hidden":
        setup = QgsEditorWidgetSetup("Hidden", {})
    elif widget == "notes":
        setup = QgsEditorWidgetSetup("TextEdit", {"IsMultiline": True, "UseHtml": False})
    elif widget == "dropdown":
        # Stored value = label. Keep labels short and never rename them later.
        choices = [{str(c): str(c)} for c in field["choices"]]
        setup = QgsEditorWidgetSetup("ValueMap", {"map": choices})
    elif widget == "lookup":
        source = lookup_layers[field["list"]]
        setup = QgsEditorWidgetSetup("ValueRelation", {
            "Layer": source.id(), "LayerName": source.name(),
            "Key": "uuid", "Value": "name", "OrderByValue": True,
            "AllowMulti": bool(field.get("multiple")), "AllowNull": True,
            "UseCompleter": True, "FilterExpression": "",
        })
    elif widget == "number":
        decimal = field["type"] == "decimal"
        config = {"Style": "SpinBox", "AllowNull": True,
                  "Step": 0.1 if decimal else 1, "Precision": 2 if decimal else 0}
        if "min" in field:
            config["Min"] = field["min"]
        if "max" in field:
            config["Max"] = field["max"]
        setup = QgsEditorWidgetSetup("Range", config)
    elif widget == "checkbox":
        setup = QgsEditorWidgetSetup("CheckBox", {"CheckedState": "", "UncheckedState": "", "TextDisplayMethod": 0})
    elif widget == "date":
        fmt = "yyyy-MM-dd HH:mm:ss" if field["type"] == "datetime" else "yyyy-MM-dd"
        setup = QgsEditorWidgetSetup("DateTime", {
            "allow_null": True, "calendar_popup": True,
            "display_format": fmt, "field_format": fmt, "field_iso_format": False,
        })
    elif widget == "photo":
        # Same settings the Mergin Maps plugin uses, plus a photos/ subfolder.
        # Paths are stored RELATIVE to the project, so they work on every device.
        setup = QgsEditorWidgetSetup("ExternalResource", {
            "DocumentViewer": 1,            # 1 = show the photo in the form
            "DocumentViewerHeight": 0, "DocumentViewerWidth": 0,
            "FileWidget": True, "FileWidgetButton": True, "FileWidgetFilter": "",
            "RelativeStorage": 1,           # 1 = relative to the project folder
            "StorageMode": 0,               # 0 = a file (not a folder)
            "PropertyCollection": {
                "name": None, "type": "collection",
                "properties": {"propertyRootPath": {
                    "active": True, "type": 3,
                    "expression": f"@project_home + '/{PHOTO_FOLDER}'",
                }},
            },
        })
    else:  # "text"
        setup = QgsEditorWidgetSetup("TextEdit", {"IsMultiline": False, "UseHtml": False})
    layer.setEditorWidgetSetup(idx, setup)

    # --- automatic value ---
    if field.get("default"):
        layer.setDefaultValueDefinition(idx, QgsDefaultValue(field["default"], bool(field.get("update"))))

    # --- required field ---
    if field.get("required"):
        layer.setFieldConstraint(idx, NOT_NULL, HARD)

    # --- rule with a message (e.g. "Dip must be between 0 and 90°") ---
    # The expression must be TRUE for a valid value. When it is false, the app
    # shows the message: hard = cannot save, soft = warning only.
    rule = field.get("constraint")
    if rule:
        layer.setConstraintExpression(idx, rule["expression"], rule.get("message", ""))
        layer.setFieldConstraint(idx, EXPRESSION, HARD if rule.get("hard", True) else SOFT)


def photo_table_fields():
    """Fields of a <layer>_photos table: one row = one photo of one feature."""
    return [
        {"name": "uuid", "type": "text", "alias": "Unique ID", "widget": "hidden", "default": "uuid()"},
        # The parent feature's uuid. The app fills it in when you add a photo
        # from the parent's form, so it stays hidden.
        {"name": "external_pk", "type": "text", "alias": "Feature", "widget": "hidden"},
        {"name": "photo", "type": "text", "alias": "Photo", "widget": "photo"},
        {"name": "caption", "type": "text", "alias": "Caption", "widget": "text"},
        {"name": "created_at", "type": "datetime", "alias": "Taken at", "widget": "hidden", "default": "now()"},
        {"name": "created_by", "type": "text", "alias": "Taken by", "widget": "hidden", "default": "@mm_username"},
    ]


def photo_table_form(child):
    """A fixed form with only Photo and Caption. With an automatic form, the
    app would show external_pk as a 'Feature' picker (mobile app
    attributecontroller.cpp, discoverRelations); the app still fills it in."""
    config = child.editFormConfig()
    config.setLayout(_enum(QgsEditFormConfig, "EditorLayout", "TabLayout"))
    root = config.invisibleRootContainer()
    root.clear()
    for name in ("photo", "caption"):
        root.addChildElement(QgsAttributeEditorField(name, child.fields().indexOf(name), root))
    child.setEditFormConfig(config)


def link_photo_table(project, parent, child):
    """Relation parent.uuid -> child.external_pk (never fid: it can change on sync)."""
    relation = QgsRelation()
    relation.setId(f"{child.name()}_relation")
    relation.setName("Photos")  # the title of the gallery in the form
    relation.setReferencedLayer(parent.id())
    relation.setReferencingLayer(child.id())
    relation.addFieldPair("external_pk", "uuid")  # (child field, parent field)
    # Composition: deleting a feature also deletes its photo rows.
    relation.setStrength(_enum(Qgis, "RelationshipStrength", "Composition")
                         if hasattr(Qgis, "RelationshipStrength")
                         else _enum(QgsRelation, "RelationStrength", "Composition"))
    if not relation.isValid():
        stop(f"could not link {child.name()} to {parent.name()}: {relation.validationError()}")
    project.relationManager().addRelation(relation)


def special_layer(project, folder, filename, layer_name, geometry, fields):
    """A GeoPackage the plugin would create for tracking or sketches."""
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        stop(f"{filename} already exists in the project folder but isn't in the project. "
             "Add it back in QGIS, or move it away, then run again.")
    CREATED_FILES.append(path)
    qfields = QgsFields()
    for name, kind in fields:
        qfields.append(QgsField(name, _TYPES[kind]))
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    writer = QgsVectorFileWriter.create(path, qfields, geometry, QgsCoordinateReferenceSystem("EPSG:4326"),
                                        QgsProject.instance().transformContext(), options)
    if writer.hasError() != WRITER_OK:
        stop(f"could not create {path}: {writer.errorMessage()}")
    del writer
    layer = QgsVectorLayer(path, layer_name, "ogr")
    make_read_only_fid(layer)
    # Editable, clickable and searchable in the app (as the plugin sets them).
    layer.setReadOnly(False)
    layer.setFlags(layer.flags() | IDENTIFIABLE | SEARCHABLE)
    return layer


def line_symbol(color, width, data_defined=False):
    symbol = QgsLineSymbol.createSimple({"line_color": color, "line_width": str(width)})
    if data_defined:  # sketches: colour and width come from each sketch
        symbol_layer = symbol.symbolLayer(0)
        symbol_layer.setDataDefinedProperty(_enum(QgsSymbolLayer, "Property", "PropertyStrokeColor"),
                                            QgsProperty.fromExpression('"color"'))
        symbol_layer.setDataDefinedProperty(_enum(QgsSymbolLayer, "Property", "PropertyStrokeWidth"),
                                            QgsProperty.fromExpression('"width"'))
    return QgsSingleSymbolRenderer(symbol)


def setup_tracking(project, folder):
    """Position tracking: same layer the Mergin Maps plugin creates."""
    existing, _ = project.readEntry("Mergin", "PositionTracking/TrackingLayer")
    if existing and existing in project.mapLayers():
        return  # the project already has one
    layer = special_layer(project, folder, "tracking_layer.gpkg", "tracking_layer", _WKB.LineStringZM, [
        ("tracking_start_time", "datetime"), ("tracking_end_time", "datetime"),
        ("total_distance", "decimal"), ("tracked_by", "text")])
    for name, expression in (("tracking_start_time", "@tracking_start_time"),
                             ("tracking_end_time", "@tracking_end_time"),
                             ("total_distance", "round($length, 2)"), ("tracked_by", "@mm_username")):
        layer.setDefaultValueDefinition(layer.fields().indexOf(name), QgsDefaultValue(expression))
    layer.setDisplayExpression("\"tracked_by\" ||' on '|| format_date( \"tracking_end_time\", 'dd MMM yyyy') "
                               "||' at '|| format_date(\"tracking_end_time\", 'H:mm (t)')")
    layer.setRenderer(line_symbol("#ffa500", 0.35))
    add_layer(project, layer)
    project.layerTreeRoot().insertLayer(0, layer)
    project.writeEntry("Mergin", "PositionTracking/TrackingLayer", layer.id())
    print("  + tracking     tracking_layer.gpkg")


def setup_sketches(project, folder):
    """Map sketching: same layer the Mergin Maps plugin creates."""
    existing, _ = project.readEntry("Mergin", "MapSketching/Layer")
    if existing and existing in project.mapLayers():
        return
    layer = special_layer(project, folder, "map_sketches.gpkg", "Map sketches", _WKB.MultiLineStringZM, [
        ("color", "text"), ("author", "text"), ("created_at", "datetime"), ("width", "decimal"),
        ("attr1", "decimal"), ("attr2", "decimal"), ("attr3", "text"), ("attr4", "text")])
    for name, expression in (("author", "@mm_username"), ("created_at", "now()"), ("width", "0.6")):
        layer.setDefaultValueDefinition(layer.fields().indexOf(name), QgsDefaultValue(expression))
    layer.setRenderer(line_symbol("#ffffff", 0.6, data_defined=True))
    add_layer(project, layer)
    project.layerTreeRoot().insertLayer(0, layer)
    project.writeEntry("Mergin", "MapSketching/Layer", layer.id())
    print("  + sketches     map_sketches.gpkg")


def filter_type(layer, field_name):
    """Pick the filter kind from the field, as the plugin's filter list allows."""
    field = layer.fields().field(field_name)
    widget = layer.editorWidgetSetup(layer.fields().indexOf(field_name))
    if widget.type() in ("ValueMap", "ValueRelation"):
        return "Multi select" if widget.config().get("AllowMulti") else "Single select"
    if widget.type() == "CheckBox" or field.typeName().lower() in ("boolean", "bool"):
        return "Checkbox"
    if field.isNumeric():
        return "Number"
    if field.typeName().lower() in ("date", "datetime"):
        return "Date"
    return "Text"


def filter_sql(kind, field_name, multi):
    """The SQL template the app fills in (copied from the plugin's field_filtering.py)."""
    field = f'"{field_name}"'
    if kind == "Text":
        return f"CAST({field} AS CHARACTER) LIKE '%@@value@@%'"
    if kind == "Number":
        return f"CAST({field} AS FLOAT) >= @@value_from@@ AND CAST({field} AS FLOAT) <= @@value_to@@"
    if kind == "Date":
        return (f"CAST({field} AS CHARACTER) >= '@@value_from@@' AND "
                f"CAST({field} AS CHARACTER) <= '@@value_to@@'")
    if kind == "Checkbox":
        return f"{field} = @@value@@"
    if not multi:
        return f"{field} IS @@value@@"
    return (f"((',' || TRIM({field}, '{{}}') || ',' ) LIKE '%,' || @@value@@ || ',%')OR"
            f"((',' || TRIM({field}, '{{}}') || ',' ) LIKE '%,\"' || @@value@@ || '\",%')")


def setup_filters(project):
    """Write the app's filter list (Mergin/Filtering/Filters)."""
    current = json.loads(project.readEntry("Mergin", "Filtering/Filters", "[]")[0] or "[]")
    for spec in FILTERS:
        layer = project.mapLayersByName(spec["layer"])[0]
        kind = spec.get("type") or filter_type(layer, spec["field"])
        multi = bool(layer.editorWidgetSetup(layer.fields().indexOf(spec["field"])).config().get("AllowMulti"))
        if any(f["layer_id"] == layer.id() and f["field_name"] == spec["field"] for f in current):
            continue  # already there
        current.append({
            "layer_id": layer.id(), "provider": layer.dataProvider().name(),
            "field_name": spec["field"], "filter_type": kind,
            "filter_name": spec.get("name") or layer.attributeDisplayName(layer.fields().indexOf(spec["field"])),
            "sql_expression": filter_sql(kind, spec["field"], multi),
            "field_has_multi_selection": multi,
        })
    project.writeEntry("Mergin", "Filtering/Enabled", True)
    project.writeEntry("Mergin", "Filtering/Filters", json.dumps(current))
    print(f"  Filters in the app: {', '.join(f['filter_name'] for f in current)}")


def write_selective_sync(folder):
    """Selective sync lives in mergin-config.json in the project folder."""
    path = os.path.join(folder, "mergin-config.json")
    config = json.load(open(path)) if os.path.exists(path) else {}
    config["input-selective-sync"] = bool(SELECTIVE_SYNC)
    config["input-selective-sync-dir"] = SELECTIVE_SYNC_FOLDER if SELECTIVE_SYNC else ""
    with open(path, "w") as out:
        json.dump(config, out, indent=2)


def apply_mergin_tab(project, folder):
    """Fill in the Mergin Maps tab. In "add" mode only what you set changes."""
    def wanted(value, default):
        return default if value is None and MODE == "new" else value

    quality = wanted(PHOTO_QUALITY, 1)
    if quality is not None:
        project.writeEntry("Mergin", "PhotoQuality", quality)
    snapping = wanted(SNAPPING, 0)
    if snapping is not None:
        project.writeEntry("Mergin", "Snapping", snapping)
        config = project.snappingConfig()
        if snapping == 2 and not config.enabled():
            config.setEnabled(True)  # "follow QGIS snapping" needs QGIS snapping on
            project.setSnappingConfig(config)
        elif snapping != 2 and config.enabled():
            print("  Note: QGIS snapping is on but the app uses its own setting "
                  f"({snapping}). Use SNAPPING = 2 to follow QGIS.")
    order = wanted(LAYER_ORDER, "qgis")
    if order is not None:
        project.writeEntry("Mergin", "SortLayersMethod/Method", 0 if order == "qgis" else 1)
    if wanted(PHOTO_SKETCHING, False) is not None:
        project.writeEntry("Mergin", "PhotoSketching/Enabled", bool(wanted(PHOTO_SKETCHING, False)))
    tracking = wanted(POSITION_TRACKING, False)
    if tracking is not None:
        project.writeEntry("Mergin", "PositionTracking/Enabled", bool(tracking))
        project.writeEntry("Mergin", "PositionTracking/UpdateFrequency",
                           1 if TRACKING_FREQUENCY is None else TRACKING_FREQUENCY)
        if tracking:
            setup_tracking(project, folder)
    sketching = wanted(MAP_SKETCHING, False)
    if sketching is not None:
        project.writeEntry("Mergin", "MapSketching/Enabled", bool(sketching))
        if sketching:
            project.writeEntry("Mergin", "MapSketching/Colors", SKETCH_COLORS or DEFAULT_SKETCH_COLORS)
            setup_sketches(project, folder)
    if FILTERS:
        setup_filters(project)


# The plugin's default sketch colours.
DEFAULT_SKETCH_COLORS = ["#ffffff", "#12181f", "#5e9ee4", "#57b46f", "#fdcb2a", "#ff9c40", "#ff8f93"]


def make_read_only_fid(layer):
    """'fid' is managed by GeoPackage and Mergin Maps: hide it from the form."""
    idx = layer.fields().indexOf("fid")
    if idx >= 0:
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("Hidden", {}))


def add_background(project):
    """Add the background map at the bottom of the layer list (read-only)."""
    if BACKGROUND == "mergin":
        uri = QgsDataSourceUri()
        uri.setParam("type", "xyz")
        uri.setParam("url", "https://tiles.merginmaps.com/data/default/{z}/{x}/{y}.pbf")
        uri.setParam("zmin", "0")
        uri.setParam("zmax", "14")
        uri.setParam("styleUrl", "https://tiles.merginmaps.com/styles/default.json")
        layer = QgsVectorTileLayer(bytes(uri.encodedUri()).decode(), "OpenMapTiles (OSM)")
        layer.loadDefaultStyle()
    elif BACKGROUND == "osm":
        layer = QgsRasterLayer(
            "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&zmax=19",
            "OpenStreetMap", "wms",
        )
    else:
        return None
    meta = layer.metadata()
    meta.setRights(["© OpenStreetMap contributors"])
    layer.setMetadata(meta)
    # Not clickable in the app, so tapping the map only finds survey features.
    layer.setFlags(layer.flags() & ~IDENTIFIABLE)
    add_layer(project, layer)
    project.layerTreeRoot().addLayer(layer)  # added last = drawn at the bottom
    return layer


# =============================================================================
# SECTION 3 · BUILD THE PROJECT
# =============================================================================

def all_new_names():
    """Every GeoPackage/layer name this script will create."""
    return ([l["name"] for l in LAYERS] + list(LOOKUP_LISTS)
            + [l["name"] + "_photos" for l in LAYERS if l.get("multiple_photos")])


def preflight(project):
    """Check EVERYTHING before writing a single file, so a mistake never
    leaves a half-built project behind. Returns (folder, crs)."""
    print(f"QGIS {Qgis.QGIS_VERSION}  ·  mode: {MODE}")
    if Qgis.QGIS_VERSION_INT < 32800:
        stop("this script needs QGIS 3.28 or newer.")
    if MODE not in ("new", "add"):
        stop("MODE must be \"new\" or \"add\".")
    if project.isDirty():
        stop("your open QGIS project has unsaved changes. Save it (or close it), then run again.")

    crs = QgsCoordinateReferenceSystem(CRS)
    if not crs.isValid():
        stop(f"'{CRS}' is not a valid CRS. Example of a valid one: 'EPSG:4326'.")

    # Names become file and column names: keep them simple so sync never trips.
    names = all_new_names()
    if len(names) != len(set(names)):
        stop("two layers or lookup lists share the same name.")
    simple = re.compile(r"[a-z][a-z0-9_]*")
    for name in names + [f["name"] for l in LAYERS for f in l["fields"]]:
        if not simple.fullmatch(name):
            stop(f"'{name}' should use only lowercase letters, numbers and _ (start with a letter).")
    for name in names:
        if name.startswith(("gpkg_", "rtree_", "sqlite_")):
            stop(f"'{name}' starts with a name GeoPackage reserves. Pick another name.")
    for name in names:
        if name in ("tracking_layer", "map_sketches"):
            stop(f"'{name}' is used by Mergin Maps for tracking/sketches. Pick another name.")

    # Mergin Maps tab values.
    checks = [(PHOTO_QUALITY, (0, 1, 2, 3), "PHOTO_QUALITY"), (SNAPPING, (0, 1, 2), "SNAPPING"),
              (TRACKING_FREQUENCY, (0, 1, 2), "TRACKING_FREQUENCY"),
              (LAYER_ORDER, ("qgis", "alphabetical"), "LAYER_ORDER")]
    for value, allowed, label in checks:
        if value is not None and value not in allowed:
            stop(f"{label} must be one of {allowed} (or None).")
    for color in SKETCH_COLORS or []:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(color)):
            stop(f"sketch colour {color!r} should look like #5e9ee4.")
    if SELECTIVE_SYNC and not re.fullmatch(r"[\w.\- /]*", SELECTIVE_SYNC_FOLDER or ""):
        stop("SELECTIVE_SYNC_FOLDER should be a folder inside the project, like 'photos'.")
    existing_layers = {l.name(): l for l in project.mapLayers().values()} if MODE == "add" else {}
    for f in FILTERS:
        spec = next((l for l in LAYERS if l["name"] == f.get("layer")), None)
        if spec:
            field_names = [x["name"] for x in spec["fields"]] + [x["name"] for x in tracking_fields()]
        elif f.get("layer") in existing_layers:
            field_names = existing_layers[f["layer"]].fields().names()
        else:
            stop(f"filter: there is no layer called {f.get('layer')!r}.")
        if f.get("field") not in field_names:
            stop(f"filter: layer {f['layer']!r} has no field {f.get('field')!r}.")
        if f.get("type") and f["type"] not in ("Text", "Number", "Date", "Checkbox",
                                               "Single select", "Multi select"):
            stop(f"filter: unknown type {f['type']!r}.")
    if MODE == "new" and not LAYERS:
        stop("LAYERS is empty: a new project needs at least one layer.")

    for layer in LAYERS:
        if layer.get("geometry") not in GEOMETRY:
            stop(f"{layer['name']}: geometry must be one of {', '.join(GEOMETRY)}.")
        for f in layer["fields"]:
            if f.get("type") not in _TYPES:
                stop(f"{layer['name']}.{f['name']}: type must be one of {', '.join(_TYPES)}.")

    # Every expression must at least be valid QGIS syntax.
    expressions = [("PHOTO_NAME", PHOTO_NAME)]
    for layer in LAYERS:
        for f in layer["fields"]:
            where = f"{layer['name']}.{f['name']}"
            if f.get("default"):
                expressions.append((where + " default", f["default"]))
            if f.get("constraint"):
                expressions.append((where + " constraint", f["constraint"]["expression"]))
            if f.get("photo_name"):
                expressions.append((where + " photo_name", f["photo_name"]))
    for where, text in expressions:
        expression = QgsExpression(text)
        if expression.hasParserError():
            stop(f"{where}: the expression is not valid QGIS syntax ({expression.parserErrorString()}).")

    if MODE == "new":
        # Start from an empty QGIS window: we never close a project for you.
        if project.fileName() or project.count():
            stop("a project is open. Start from an empty one (Project > New), then run again.")
        if not simple.fullmatch(PROJECT_NAME.replace("-", "_")):
            stop("PROJECT_NAME should use only lowercase letters, numbers, - and _.")
        folder = os.path.join(PARENT_FOLDER, PROJECT_NAME)
        if os.path.exists(folder) and os.listdir(folder):
            stop(f"{folder} already exists and is not empty. Pick another PROJECT_NAME, "
                 "or use MODE = \"add\" to add layers to that project.")
    else:
        # Add to the project that is open right now (e.g. downloaded with the plugin).
        if not project.fileName():
            stop("MODE is \"add\": open your Mergin Maps project in QGIS first, then run again.")
        folder = os.path.dirname(project.fileName())
        if not os.path.isdir(os.path.join(folder, ".mergin")):
            print("  Note: no .mergin folder here, so this is not (yet) a Mergin Maps project.\n"
                  "        That's fine: upload it with the plugin when you're done.")
        existing = {l.name() for l in project.mapLayers().values()}
        for name in names:
            if name in existing:
                stop(f"the project already has a layer called '{name}'. Rename it in LAYERS.")
            if os.path.exists(os.path.join(folder, name + ".gpkg")):
                stop(f"{name}.gpkg already exists in the project folder. Rename it in LAYERS.")
    return folder, crs


def build():
    project = QgsProject.instance()

    # Step 1 · Safety checks (nothing is written before these pass) ----------
    folder, crs = preflight(project)

    # Step 2 · Folders and project file ----------------------------------------
    if MODE == "new":
        if not os.path.exists(folder):
            CREATED_FILES.append(folder)
        os.makedirs(folder, exist_ok=True)
        project.setFileName(os.path.join(folder, PROJECT_NAME + ".qgz"))
        project.setCrs(crs)
        project.setTitle(TITLE)
    else:
        # Keep a copy of the project file OUTSIDE the project folder (so it is
        # never synced), in case you want to go back. Mergin Maps also keeps
        # every synced version in the project history.
        backups = os.path.join(os.path.expanduser("~"), "MerginMaps backups")
        os.makedirs(backups, exist_ok=True)
        backup = os.path.join(backups, os.path.basename(project.fileName()) + "."
                              + time.strftime("%Y%m%d-%H%M%S") + ".bak")
        shutil.copy2(project.fileName(), backup)
        print(f"  Backup of the project file: {backup}")
    photos = os.path.join(folder, PHOTO_FOLDER)
    if not os.path.exists(photos):
        CREATED_FILES.append(photos)
    os.makedirs(photos, exist_ok=True)
    print(f"Project folder: {folder}")

    # Step 3 · Lookup lists: one non-spatial GeoPackage each ------------------
    lookup_layers = {}
    for list_name, values in LOOKUP_LISTS.items():
        layer = create_geopackage(folder, list_name, "none",
                                  [{"name": "uuid", "type": "text"}, {"name": "name", "type": "text"}], crs)
        layer.setDefaultValueDefinition(layer.fields().indexOf("uuid"), QgsDefaultValue("uuid()", False))
        layer.setEditorWidgetSetup(layer.fields().indexOf("uuid"), QgsEditorWidgetSetup("Hidden", {}))
        layer.setFieldAlias(layer.fields().indexOf("name"), "Name")
        make_read_only_fid(layer)
        # Fill the starting values (each gets its own UUID).
        layer.startEditing()
        for value in values:
            feature = QgsVectorLayerUtils.createFeature(layer)  # fills uuid()
            feature["name"] = value
            layer.addFeature(feature)
        if not layer.commitChanges():
            stop(f"could not save the values of {list_name}: {layer.commitErrors()}")
        layer.setDisplayExpression('"name"')
        add_layer(project, layer)
        lookup_layers[list_name] = layer
        print(f"  + lookup list  {list_name}.gpkg  ({len(values)} values)")

    # Step 4 · Survey layers: one GeoPackage each ------------------------------
    survey_layers = []
    for spec in LAYERS:
        fields = list(spec["fields"])
        if ADD_TRACKING_FIELDS:
            fields = tracking_fields() + fields
            if spec["geometry"] == "point":
                # GPS accuracy (metres) when the point was captured.
                fields.insert(5, {"name": "gps_accuracy", "type": "decimal", "alias": "GPS accuracy (m)",
                                  "widget": "hidden",
                                  # only when the point was placed at the GPS position
                                  "default": "if(@position_from_gps, @position_horizontal_accuracy, NULL)"})
        elif spec.get("multiple_photos"):
            # The photo table links on uuid, so this layer needs one anyway.
            fields = [tracking_fields()[0]] + fields
        if ADD_SPARE_FIELDS:
            fields = fields + spare_fields()

        layer = create_geopackage(folder, spec["name"], spec["geometry"], fields, crs)
        make_read_only_fid(layer)
        for field in fields:
            setup_field(layer, field, lookup_layers)

        # Title shown for each feature in the app's lists and preview panel.
        if spec.get("title"):
            layer.setDisplayExpression(f'"{spec["title"]}"')

        # Simple, clear symbol in the chosen colour.
        if spec["geometry"] != "none":
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(QColor(spec.get("color", "#e1312d")))
            layer.renderer().setSymbol(symbol)

        add_layer(project, layer)
        survey_layers.append(layer)

        # Photo file names, e.g. trees-sarah-261102143005.jpg (unique per photo).
        for field in fields:
            if field.get("widget") == "photo":
                project.writeEntry("Mergin", f"PhotoNaming/{layer.id()}/{field['name']}",
                                   field.get("photo_name", PHOTO_NAME))
        print(f"  + survey layer {spec['name']}.gpkg  ({spec['geometry']}, {len(fields)} fields)")

    # Step 5 · Photo tables: several photos per feature --------------------
    # One table per layer that asked for it, in its own GeoPackage. In the
    # app, the parent form shows a gallery with an "add photo" button.
    photo_tables = []
    for spec, parent in zip(LAYERS, survey_layers):
        if not spec.get("multiple_photos"):
            continue
        fields = photo_table_fields()
        child = create_geopackage(folder, spec["name"] + "_photos", "none", fields, crs)
        make_read_only_fid(child)
        for field in fields:
            setup_field(child, field, lookup_layers)
        child.setDisplayExpression('coalesce("caption", "photo")')
        photo_table_form(child)
        add_layer(project, child)
        project.writeEntry("Mergin", f"PhotoNaming/{child.id()}/photo", PHOTO_NAME)
        link_photo_table(project, parent, child)
        photo_tables.append(child)
        print(f"  + photo table  {child.name()}.gpkg  (linked to {parent.name()} by uuid)")

    # Step 6 · Layer list: new survey layers on top, tables in groups --------
    root = project.layerTreeRoot()
    for position, layer in enumerate(survey_layers):
        root.insertLayer(position, layer)  # above any existing layers
    for title, tables in (("Photo tables", photo_tables), ("Lookup lists", list(lookup_layers.values()))):
        if tables:
            group = root.findGroup(title) or root.addGroup(title)
            for layer in tables:
                group.addLayer(layer)
                # Non-spatial tables must be searchable to browse them in the app.
                layer.setFlags(layer.flags() | SEARCHABLE)

    # Step 7 · Project settings Mergin Maps relies on --------------------------
    # Relative paths: the project works wherever the folder is copied.
    project.setFilePathStorage(_enum(Qgis, "FilePathType", "Relative"))
    project.writeEntry("Paths", "/Absolute", False)
    project.setPresetHomePath("")
    if MODE == "new":
        add_background(project)
        # "Zoom to project" extent in the app.
        if AREA_OF_INTEREST:
            west, south, east, north = AREA_OF_INTEREST
            to_project = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs, project)
            extent = to_project.transformBoundingBox(QgsRectangle(west, south, east, north))
            project.viewSettings().setPresetFullExtent(QgsReferencedRectangle(extent, crs))
    else:
        # Your project's CRS, background and extent are left as they are.
        print("  Existing layers and data were not changed.")
    # The Mergin Maps tab (photo quality, snapping, tracking, sketching, ...).
    apply_mergin_tab(project, folder)

    # Step 8 · Save ------------------------------------------------------------
    if not project.write():
        stop(f"could not save {project.fileName()}")
    if SELECTIVE_SYNC is not None:
        write_selective_sync(folder)

    # If this runs inside QGIS, zoom the map to the area of interest.
    try:
        from qgis.utils import iface
        if iface and MODE == "new" and AREA_OF_INTEREST:
            iface.mapCanvas().setExtent(project.viewSettings().presetFullExtent())
            iface.mapCanvas().refresh()
    except Exception:
        pass

    # Step 9 · Summary and next steps ------------------------------------------
    print("\nDone. Your project is ready:")
    print(f"  {project.fileName()}")
    print("\nNext steps:")
    print("  1. Look at each new layer's form: Layer Properties > Attributes Form.")
    if MODE == "new":
        print("  2. Mergin Maps toolbar > Create Mergin Maps project >")
        print("     'Use current QGIS project as is', then choose a project name.")
        print("     (The name cannot be changed later.)")
    else:
        print("  2. Mergin Maps toolbar > Synchronise: the new .gpkg files and the")
        print("     project file are uploaded. Everyone then syncs their phone.")
    print("  3. On a phone: download/sync the project, capture a test feature with")
    print("     a photo, sync, and check it in QGIS.")
    print("\nRemember: change aliases, not field names. To add a question later,")
    print("use a spare field instead of adding a new column.")


try:
    build()
except Exception as error:
    # Undo this run: remove the layers and files it created (and only those).
    undo(QgsProject.instance())
    if isinstance(error, RuntimeError) and "STOPPED" in str(error):
        raise  # a clear message from stop()
    raise RuntimeError(
        f"\n\n  Something went wrong: {error}\n"
        "  Everything this run created was removed again; your existing layers\n"
        "  and data were not touched. Fix the problem and run the script again.\n") from error
