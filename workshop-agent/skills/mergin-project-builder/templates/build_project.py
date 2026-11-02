"""
===============================================================================
  MERGIN MAPS PROJECT BUILDER  ·  {{PROJECT_TITLE}}
===============================================================================

What this script does
---------------------
It builds a ready-to-sync Mergin Maps project folder on your computer:

    {{PROJECT_NAME}}/
    ├── {{PROJECT_NAME}}.qgz      <- the QGIS project (relative paths)
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

Made for: QGIS {{QGIS_VERSION}}  (tested with QGIS 3.28 or newer, and QGIS 4)
Generated on: {{DATE}}
===============================================================================
"""

import os

# =============================================================================
# SECTION 1 · SETTINGS  (edit here)
# =============================================================================

# --- Where to create the project ---------------------------------------------
# The project folder is created INSIDE this folder. Use a local drive:
# network drives are not supported by Mergin Maps.
# os.path.expanduser("~") is your home folder (works on Windows, macOS and Linux).
PARENT_FOLDER = os.path.join(os.path.expanduser("~"), "{{PARENT_FOLDER}}")

# Name of the project folder and the .qgz file. Use letters, numbers, "-" or "_".
# Tip: you choose the Mergin Maps project name when you upload it, and that
# name cannot be changed later, so pick it carefully.
PROJECT_NAME = "{{PROJECT_NAME}}"

# --- Coordinate reference system ---------------------------------------------
# Used for the project and for the new layers.
# EPSG:4326 (WGS 84, latitude/longitude) is the default: it is what GPS uses.
# For accurate lengths and areas, use a local projected CRS instead,
# e.g. "EPSG:26910" (UTM zone 10N, northern California).
CRS = "{{CRS}}"

# --- Area of interest (optional) ---------------------------------------------
# The "Zoom to project" button in the app zooms here.
# Longitude/latitude box: [west, south, east, north]. Set to None to skip.
AREA_OF_INTEREST = {{AREA_OF_INTEREST}}

# --- Background map ----------------------------------------------------------
#   "mergin" -> Mergin Maps vector tiles (OpenStreetMap data, online,
#               free for Mergin Maps users, light on mobile data)
#   "osm"    -> standard OpenStreetMap raster tiles (online)
#   None     -> no background map
BACKGROUND = "{{BACKGROUND}}"

# --- Mergin Maps app settings ------------------------------------------------
# Photo size saved by the app: 0 = original, 1 = high, 2 = medium, 3 = low
PHOTO_QUALITY = {{PHOTO_QUALITY}}
# Snapping in the app: 0 = none, 1 = basic, 2 = follow QGIS snapping settings
SNAPPING = {{SNAPPING}}
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
LOOKUP_LISTS = {{LOOKUP_LISTS}}

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
LAYERS = {{LAYERS}}


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


GEOMETRY = {
    "point": _enum(Qgis, "WkbType", "Point") if hasattr(Qgis, "WkbType") else 1,
    "line": _enum(Qgis, "WkbType", "LineString") if hasattr(Qgis, "WkbType") else 2,
    "polygon": _enum(Qgis, "WkbType", "Polygon") if hasattr(Qgis, "WkbType") else 3,
    "none": _enum(Qgis, "WkbType", "NoGeometry") if hasattr(Qgis, "WkbType") else 100,
}
NOT_NULL = _enum(QgsFieldConstraints, "Constraint", "ConstraintNotNull")
EXPRESSION = _enum(QgsFieldConstraints, "Constraint", "ConstraintExpression")
HARD = _enum(QgsFieldConstraints, "ConstraintStrength", "ConstraintStrengthHard")
SOFT = _enum(QgsFieldConstraints, "ConstraintStrength", "ConstraintStrengthSoft")


def stop(message):
    """Stop the script with a clear message (nothing half-built is left behind)."""
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
    if writer.hasError() != QgsVectorFileWriter.NoError:
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
                         if hasattr(Qgis, "RelationshipStrength") else QgsRelation.Composition)
    if not relation.isValid():
        stop(f"could not link {child.name()} to {parent.name()}: {relation.validationError()}")
    project.relationManager().addRelation(relation)


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
    layer.setFlags(layer.flags() & ~QgsMapLayer.Identifiable)
    project.addMapLayer(layer, False)
    project.layerTreeRoot().addLayer(layer)  # added last = drawn at the bottom
    return layer


# =============================================================================
# SECTION 3 · BUILD THE PROJECT
# =============================================================================

def build():
    project = QgsProject.instance()
    folder = os.path.join(PARENT_FOLDER, PROJECT_NAME)

    # Step 1 · Safety checks ---------------------------------------------------
    print(f"QGIS {Qgis.QGIS_VERSION}")
    if Qgis.QGIS_VERSION_INT < 32800:
        stop("this script needs QGIS 3.28 or newer.")
    if project.isDirty():
        stop("your open QGIS project has unsaved changes. Save or close it, then run again.")
    if os.path.exists(folder) and os.listdir(folder):
        stop(f"{folder} already exists and is not empty. Pick another PROJECT_NAME or move that folder.")
    crs = QgsCoordinateReferenceSystem(CRS)
    if not crs.isValid():
        stop(f"'{CRS}' is not a valid CRS. Example of a valid one: 'EPSG:4326'.")
    names = ([l["name"] for l in LAYERS] + list(LOOKUP_LISTS)
             + [l["name"] + "_photos" for l in LAYERS if l.get("multiple_photos")])
    if len(names) != len(set(names)):
        stop("two layers or lookup lists share the same name.")
    # Names become file and column names: keep them simple so sync never trips.
    import re
    simple = re.compile(r"^[a-z][a-z0-9_]*$")
    for name in names + [f["name"] for l in LAYERS for f in l["fields"]]:
        if not simple.match(name):
            stop(f"'{name}' should use only lowercase letters, numbers and _ (start with a letter).")

    # Step 2 · Start a clean project and create the folders -------------------
    project.clear()
    os.makedirs(os.path.join(folder, PHOTO_FOLDER), exist_ok=True)
    project.setFileName(os.path.join(folder, PROJECT_NAME + ".qgz"))
    project.setCrs(crs)
    project.setTitle(PROJECT_NAME)
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
        layer.commitChanges()
        layer.setDisplayExpression('"name"')
        project.addMapLayer(layer, False)
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
                                  "widget": "hidden", "default": "@position_horizontal_accuracy"})
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

        project.addMapLayer(layer, False)
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
        project.addMapLayer(child, False)
        project.writeEntry("Mergin", f"PhotoNaming/{child.id()}/photo", PHOTO_NAME)
        link_photo_table(project, parent, child)
        photo_tables.append(child)
        print(f"  + photo table  {child.name()}.gpkg  (linked to {parent.name()} by uuid)")

    # Step 6 · Layer order: survey layers on top, lookup lists, background last
    root = project.layerTreeRoot()
    for layer in survey_layers:
        root.addLayer(layer)
    if photo_tables:
        group = root.addGroup("Photo tables")
        for layer in photo_tables:
            group.addLayer(layer)
            layer.setFlags(layer.flags() | QgsMapLayer.Searchable)
    if lookup_layers:
        group = root.addGroup("Lookup lists")
        for layer in lookup_layers.values():
            group.addLayer(layer)
            # Non-spatial tables must be searchable to browse them in the app.
            layer.setFlags(layer.flags() | QgsMapLayer.Searchable)
    add_background(project)

    # Step 7 · Project settings Mergin Maps relies on --------------------------
    # Relative paths: the project works wherever the folder is copied.
    project.setFilePathStorage(_enum(Qgis, "FilePathType", "Relative"))
    project.writeEntry("Paths", "/Absolute", False)
    project.setPresetHomePath("")
    # Mergin Maps app settings (same keys the Mergin Maps plugin writes).
    project.writeEntry("Mergin", "PhotoQuality", PHOTO_QUALITY)
    project.writeEntry("Mergin", "Snapping", SNAPPING)
    project.writeEntry("Mergin", "SortLayersMethod/Method", 0)  # keep QGIS layer order
    # "Zoom to project" extent in the app.
    if AREA_OF_INTEREST:
        west, south, east, north = AREA_OF_INTEREST
        to_project = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs, project)
        extent = to_project.transformBoundingBox(QgsRectangle(west, south, east, north))
        project.viewSettings().setPresetFullExtent(QgsReferencedRectangle(extent, crs))

    # Step 8 · Save ------------------------------------------------------------
    if not project.write():
        stop(f"could not save {project.fileName()}")

    # If this runs inside QGIS, zoom the map to the area of interest.
    try:
        from qgis.utils import iface
        if iface and AREA_OF_INTEREST:
            iface.mapCanvas().setExtent(project.viewSettings().presetFullExtent())
            iface.mapCanvas().refresh()
    except Exception:
        pass

    # Step 9 · Summary and next steps ------------------------------------------
    print("\nDone. Your project is ready:")
    print(f"  {project.fileName()}")
    print("\nNext steps:")
    print("  1. Look at each layer's form: Layer Properties > Attributes Form.")
    print("  2. Mergin Maps toolbar > Create Mergin Maps project >")
    print("     'Use current QGIS project as is', then choose a project name.")
    print("     (The name cannot be changed later.)")
    print("  3. Open the Mergin Maps app on your phone, download the project,")
    print("     and capture a test feature with a photo. Sync, then check it in QGIS.")
    print("\nRemember: change aliases, not field names. To add a question later,")
    print("use a spare field instead of adding a new column.")


build()
