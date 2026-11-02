# Mergin Maps project guidelines

The rules the builder follows, each with its source. Gathered 2026-11-02 from
the Mergin Maps docs (github.com/MerginMaps/docs), blog, QGIS plugin
(github.com/MerginMaps/qgis-plugin) and mobile app (github.com/MerginMaps/mobile).

Sources
- **BP**: "Mergin Maps best practices: From setup to fieldwork", Vitor Vieira, 2026-09-16. https://merginmaps.com/blog/mergin-maps-best-practises-from-setup-to-fieldwork
- **PREP**: https://merginmaps.com/docs/gis/features/
- **PHOTOS**: https://merginmaps.com/docs/layer/photos/
- **DEFAULTS**: https://merginmaps.com/docs/layer/default-values/
- **VARS**: https://merginmaps.com/docs/layer/variables/
- **SELECT**: https://merginmaps.com/docs/layer/value-select/
- **REL**: https://merginmaps.com/docs/layer/relations/
- **DEPLOY**: https://merginmaps.com/docs/manage/deploy-new-project/
- **PROJECT**: https://merginmaps.com/docs/manage/project/
- **MAPS**: https://merginmaps.com/docs/gis/settingup_background_map/
- **NAMES**: https://merginmaps.com/docs/gis/photo-names/
- **TOOBIG**: https://merginmaps.com/blog/support-tip-what-to-do-if-your-project-is-too-big
- **COND**: https://merginmaps.com/blog/support-tip---using-conditions-to-improve-your-mergin-maps-survey
- **PLUGIN**: `Mergin/validation.py`, `Mergin/utils.py` (`create_basic_qgis_project`), `Mergin/project_settings_widget.py`
- **APP**: `app/inpututils.cpp`, `app/attributes/attributecontroller.cpp`

## 1. Files and folders

| Rule | Why | Source | Builder |
|---|---|---|---|
| Every survey layer (spatial or table) is a GeoPackage | Only GeoPackage edits are merged by sync; other formats get overwritten and end up in conflict files | BP #1, PREP | ✅ |
| One GeoPackage per layer; never add a table to a GeoPackage that is already syncing | Adding a table restructures the file and creates conflicting copies | BP #2, PREP | ✅ |
| All data, SVG symbols, offline maps and PDFs live inside the project folder | Only that folder syncs | BP #6, PROJECT | ✅ (layers at folder root) |
| Project paths are Relative; no preset home path | The app resolves everything from the project folder | PREP, PLUGIN (ABSOLUTE_PATHS, PROJECT_HOME_PATH) | ✅ |
| Exactly one .qgs/.qgz in the folder | Plugin stops validating otherwise | PLUGIN (MULTIPLE_PROJS) | ✅ |
| Local drive, not a network drive | SQLite over the network corrupts/syncs badly | PROJECT | ✅ (asked) |
| Rasters as GeoTIFF or in their own GeoPackage; offline basemaps as MBTiles in the folder | Sync and app support | PREP, MAPS | n/a |
| Keep projects under ~8 GB; side-load huge basemaps (Android) | Sync time, device storage | BP #20, TOOBIG | n/a |
| File names without `<>:|?*"` or control characters | Server refuses the upload | PLUGIN (INVALID_ADDED_FILENAME) | ✅ |

## 2. Schema (hard to change later)

| Rule | Why | Source | Builder |
|---|---|---|---|
| Plan types up front: text for names/codes, integer for counts, decimal for measurements, date/datetime for time; not everything as text | Types are the hardest thing to change after deployment | BP #3 | ✅ (asked per field) |
| Add hidden spare fields of several types | Exposing one later is a form change, not a schema change | BP #4, PREP | ✅ |
| Add a `uuid` field (default `uuid()`, no "apply on update"); link tables on it, never on `fid` | fid can change during sync | BP #5, REL, PHOTOS, PLUGIN (FIELD_IS_PRIMARY_KEY) | ✅ |
| Rename = change alias; remove = hide from form | Renaming/deleting changes the schema | BP #9, PREP | ✅ (in script notes) |
| Schema changes during a survey need the redeploy procedure | Unsynced devices lose features | BP #21, DEPLOY | ✅ (in script notes) |
| Field names: no `\ / ( ) [ ] { } "` or newlines | Plugin warning INCORRECT_FIELD_NAME | PLUGIN | ✅ (stricter: `^[a-z][a-z0-9_]*$`) |
| Geometry: Point, LineString, Polygon (or Multi), No Geometry for tables | Supported types | PREP | ✅ (single-part) |

## 3. Forms

| Rule | Why | Source | Builder |
|---|---|---|---|
| Prefer Value Map / Value Relation over free text | No typos, consistent data | BP #7, SELECT | ✅ dropdown / lookup |
| Value Relation when values must grow in the field, need search or multi-select; key on a uuid field | Editable in the app; fid is unstable | SELECT | ✅ lookup |
| `fid` hidden / not editable | Managed by GeoPackage and sync | Tutorial, PLUGIN basic project | ✅ |
| Required fields: Not null, enforced (hard) | App blocks saving until filled | BP #7, APP fieldvalidator | ✅ |
| Automatic values: `@mm_username`, `now()`, `uuid()`, `@position_horizontal_accuracy`; "apply on update" for last-editor fields | No typing; consistent audit trail | BP #8, DEFAULTS, VARS | ✅ |
| Defaults apply to hidden fields too; "apply on update" makes a field read-only in the app | App behaviour | APP attributecontroller | ✅ |
| Supported widgets in the app: TextEdit, Range (SpinBox/Slider), DateTime, CheckBox, ValueMap, ValueRelation, ExternalResource, RelationReference, Relation, Hidden. Others fall back to text | App behaviour | APP inpututils.cpp | ✅ |
| Tabs show in the app only if every top-level form item is a tab; otherwise one page with group headers | App behaviour | APP attributecontroller | not generated |
| Conditional visibility works on containers (groups/tabs), not single fields | App behaviour | APP, COND | not generated |
| Feature title = layer display expression | Lists and preview panel | PREP, APP | ✅ (`title`) |

## 4. Photos

| Rule | Why | Source | Builder |
|---|---|---|---|
| Text field + Attachment (ExternalResource) widget | How the app captures photos | PHOTOS | ✅ |
| Store paths relative to project (`RelativeStorage = 1`), never absolute | Paths must work on every device | PHOTOS, PLUGIN (ATTACHMENT_*) | ✅ |
| Photo folder by data-defined expression `@project_home + '/photos'`, not a fixed DefaultRoot | Plugin warns on fixed roots | PHOTOS, PLUGIN | ✅ |
| Set photo quality explicitly (High = 1) | Originals can exceed 10 MB | BP #17, TOOBIG | ✅ default High |
| Photo names unique; no `|?*"`; `.jpg` added automatically | Sync safety | NAMES | ✅ default `layer-user-timestamp` |
| Several photos per feature: child table (`photo`, `external-pk`) related on the parent uuid + Relation widget | One field holds one photo | PHOTOS | ✅ `multiple_photos` → `<layer>_photos.gpkg`, `external_pk` → parent `uuid`, Composition |
| The app turns a relation into a gallery when the child table has a photo (ExternalResource) field; it uses the first one, unless the relation label contains "nogallery" | App behaviour | APP relationfeaturesmodel.cpp, inpututils.cpp | ✅ one photo field per table |
| Don't put a single photo field on a layer that also has a photo gallery | Gallery photos can overwrite the parent's photo | [mobile#2029](https://github.com/MerginMaps/mobile/issues/2029) | ✅ render.py warns |
| Selective sync on the photos folder when surveyors don't need each other's photos | Data use, sync time | BP #19 | ✅ `selective_sync` |

## 5. Project settings (`QgsProject.writeEntry("Mergin", key, value)`)

| Key | Values | Builder |
|---|---|---|
| `PhotoQuality` | 0 original, 1 high, 2 medium, 3 low | ✅ |
| `Snapping` | 0 none, 1 basic, 2 follow QGIS | ✅ |
| `SortLayersMethod/Method` | 0 QGIS order, 1 alphabetical (app default) | ✅ 0 |
| `PhotoNaming/<layer_id>/<field>` | expression | ✅ |
| `PositionTracking/Enabled`, `/UpdateFrequency`, `/TrackingLayer` | bool, 0 best / 1 normal / 2 low, layer id (`tracking_layer.gpkg`, LineStringZM, EPSG:4326, plugin recipe) | ✅ |
| `MapSketching/Enabled`, `/Layer`, `/Colors` | bool, layer id (`map_sketches.gpkg`, plugin recipe), list of hex | ✅ |
| `PhotoSketching/Enabled` | bool | ✅ |
| `Filtering/Enabled`, `Filtering/Filters` | bool, JSON list `{layer_id, provider, field_name, filter_type, filter_name, sql_expression, field_has_multi_selection}`; the app needs `sql_expression` (it doesn't generate it) | ✅ same SQL templates as the plugin |
| Selective sync: `mergin-config.json` in the project folder | `{"input-selective-sync": bool, "input-selective-sync-dir": "photos"}` | ✅ |
| Snapping 2 needs QGIS snapping on (plugin warning QGIS_SNAPPING_NOT_ENABLED) | | ✅ turned on |

Also: set a project full extent (Zoom to project), mark background/reference
layers read-only and not identifiable, make non-spatial tables searchable.
Source: PREP. Builder: ✅

## 6. Background maps

- Default in the plugin's basic project: Mergin Maps vector tiles
  (`https://tiles.merginmaps.com/...`, OSM data, free for Mergin Maps users,
  attribution "© OpenMapTiles © OpenStreetMap contributors"). Source: PLUGIN, MAPS.
- XYZ / WMS / vector tile URLs need a connection. For offline: right-click the
  vector tile layer > "Make available offline…" (MBTiles in the project folder). Source: MAPS, BP #16.
- Raster XYZ with labels: tile resolution "Standard" so text is readable on phones. Source: MAPS.

## 7. CRS

No Mergin Maps source prescribes a CRS. Agreed for this builder: **EPSG:4326 by
default** (what GPS reports). Offer a local projected CRS (e.g. UTM, State
Plane) when the user needs accurate lengths/areas or a basemap in that CRS.
Avoid datum shifts that need grid files; if one is needed, the grid must be in
`<project>/proj/` (PLUGIN MISSING_DATUM_SHIFT_GRID).

## 8. QGIS versions

- QGIS 4 writes some settings QGIS 3 cannot read (canvas CRS, sketching, photo
  naming, tracking show as unset). The app reads both. The whole team should use
  the same major version. Source: PREP.
- The template runs on QGIS 3.28+ and is written for QGIS 4 (Qt 6 enums,
  QMetaType field types). Tested on QGIS 3.42.

## 9. Before the field

Test on a real phone: capture in every layer, take a photo, try a save that
should fail (required field), sync, check in QGIS. Repeat offline. Surveyors get
the Editor role, the maintainer Writer. Source: BP #10, #14.

## 10. Known bug workarounds (from confirmed GitHub bugs, checked 2026-11-02)

Run `scripts/known_bugs.py <spec>.json` for the current list; these are the
ones already built into the design rules.

| Bug | Effect | Rule | Builder |
|---|---|---|---|
| [mobile#1694](https://github.com/MerginMaps/mobile/issues/1694) | A visible, auto-generated `fid` in the form gives "Value must be a number" and blocks saving | Hide `fid` | ✅ |
| [mobile#2984](https://github.com/MerginMaps/mobile/issues/2984) | Adding a new photo field to a deployed layer crashes the app on sync | Add a photo later by switching a spare text field to the Attachment widget, not by adding a column | ✅ spare text fields |
| [mobile#4417](https://github.com/MerginMaps/mobile/issues/4417) | A default value that references another field in the same form may not apply when adding a feature | Defaults use variables/functions only (`now()`, `@mm_username`, `uuid()`, `@position_*`), not other fields | ✅ (agent rule) |
| [mobile#1516](https://github.com/MerginMaps/mobile/issues/1516), [#4564](https://github.com/MerginMaps/mobile/issues/4564) | Range slider without min/max is unusable | Always give number fields a `min` and `max` | ✅ (render.py warns) |
| [mobile#4758](https://github.com/MerginMaps/mobile/issues/4758) | Value Map on a Date field doesn't show the saved value | Dropdowns only on text/integer fields | ✅ (render.py) |
| [mobile#4696](https://github.com/MerginMaps/mobile/issues/4696), [#4549](https://github.com/MerginMaps/mobile/issues/4549) | Value Relation filter expressions unreliable (labels, dependent fields) | Avoid filtered/drill-down lookups, or test them on a phone | not generated |
| [mobile#4053](https://github.com/MerginMaps/mobile/issues/4053), [#1496](https://github.com/MerginMaps/mobile/issues/1496) | "Reuse last value" misbehaves with lookups and defaults | Don't turn on reuse-last-value for those fields | n/a |
| [mobile#4060](https://github.com/MerginMaps/mobile/issues/4060) | Turning selective sync on in a running project can leave phones in a "pending" state | Decide on selective sync when the project is created; avoid toggling it mid-survey | ✅ set at creation |
| [qgis-plugin#899](https://github.com/MerginMaps/qgis-plugin/issues/899) | The selective sync folder isn't always saved from the Project Properties dialog | The script writes `mergin-config.json` directly | ✅ |
| [mobile#4588](https://github.com/MerginMaps/mobile/issues/4588) | Position tracking stops while the screen is off on Android | Tell surveyors to keep the screen on while tracking (agent says so when tracking is on) | ✅ (agent rule) |
