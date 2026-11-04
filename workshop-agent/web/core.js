/* Mergin Maps project builder, browser edition: the parts with no page in them.
   Ports of the skill's scripts so the web page builds the same files:
   - checkSettings / checkSpec / fillAliases  <- scripts/render.py
   - previewText                              <- scripts/preview.py
   - renderScript                             <- scripts/render.py main()
   - formPreviewHtml                          <- scripts/form_preview.py
   Keep these in step with the Python versions when the skill changes. */
(function (root) {
  "use strict";

  const AUTOMATIC = new Set(["fid", "uuid", "created_at", "created_by", "updated_at", "updated_by", "gps_accuracy"]);
  const WIDGET_TYPES = {
    text: null, notes: ["text"], hidden: null,
    dropdown: ["text", "integer"], lookup: ["text"], photo: ["text"],
    number: ["integer", "decimal"], checkbox: ["boolean"], date: ["date", "datetime"],
  };
  const NAME = /^[a-z][a-z0-9_]*$/;
  const TYPES = ["boolean", "date", "datetime", "decimal", "integer", "text"];
  const RESERVED_PREFIX = /^(gpkg_|rtree_|sqlite_)/;
  const FREQUENCY = { best: 0, normal: 1, low: 2 };
  const isNum = (v) => typeof v === "number" && Number.isFinite(v);

  // ---------- render.py: app_settings ----------
  function appSettings(spec) {
    const app = Object.assign({}, spec.app_settings || {});
    for (const key of ["photo_quality", "snapping"]) {
      if (key in spec && !(key in app)) app[key] = spec[key];
    }
    if (typeof app.tracking_frequency === "string") {
      const k = app.tracking_frequency.toLowerCase();
      if (k in FREQUENCY) app.tracking_frequency = FREQUENCY[k];
    }
    return app;
  }

  // ---------- render.py: check_settings ----------
  function checkSettings(spec, errors, warnings) {
    if ("project_name" in spec && !/^[a-z0-9][a-z0-9_-]{0,59}$/.test(String(spec.project_name)))
      errors.push(`project_name: "${spec.project_name}" is not allowed (lowercase letters, numbers, - and _)`);
    if (!spec.project_name) errors.push("project_name is missing");
    if ("crs" in spec && !/^[A-Za-z]+:[0-9A-Za-z_]+$/.test(String(spec.crs)))
      errors.push(`crs: "${spec.crs}" is not allowed (like EPSG:4326)`);
    if ("qgis_version" in spec && !/^[0-9]+(\.[0-9x]+)*$/.test(String(spec.qgis_version)))
      errors.push(`qgis_version: "${spec.qgis_version}" is not allowed (like 3.42)`);
    const folder = String(spec.parent_folder ?? "MerginMaps Projects");
    const parts = folder.replace(/\\/g, "/").split("/");
    if (folder.startsWith("/") || /^[A-Za-z]:/.test(folder) || parts.includes("..")
        || !/^[\p{L}\p{N}_ .\-/]+$/u.test(folder) || folder.replace(/^\/+/, "").startsWith(".")
        || ["Library", "AppData"].includes(parts[0]))
      errors.push(`parent_folder: "${folder}" must be a simple folder inside your home folder`);
    if (/onedrive|dropbox|google ?drive|icloud/i.test(folder))
      warnings.push("parent_folder is a cloud-synced folder; GeoPackages can get corrupted there. Use a plain local folder.");
    const mode = spec.mode ?? "new";
    if (!["new", "add"].includes(mode)) errors.push("mode must be 'new' or 'add'");
    const bg = spec.background === undefined ? "mergin" : spec.background;
    if (!["mergin", "osm", null].includes(bg)) errors.push("background must be 'mergin', 'osm' or null");
    const app = appSettings(spec);
    const allowed = { photo_quality: [0, 1, 2, 3], snapping: [0, 1, 2], tracking_frequency: [0, 1, 2],
      layer_order: ["qgis", "alphabetical"] };
    for (const [key, values] of Object.entries(allowed)) {
      const v = app[key];
      if (v !== undefined && v !== null && (typeof v === "boolean" || !values.includes(v)))
        errors.push(`app_settings.${key} must be one of ${values.join(", ")}`);
    }
    for (const key of ["position_tracking", "map_sketching", "photo_sketching", "selective_sync"]) {
      if (app[key] !== undefined && app[key] !== null && typeof app[key] !== "boolean")
        errors.push(`app_settings.${key} must be true or false`);
    }
    for (const c of app.sketch_colors || []) {
      if (!/^#[0-9a-fA-F]{6}$/.test(String(c))) errors.push(`app_settings.sketch_colors: "${c}" should look like #5e9ee4`);
    }
    if ((app.sketch_colors || []).length > 7) errors.push("app_settings.sketch_colors: at most 7 colours");
    const sf = String(app.selective_sync_folder ?? "photos");
    if (!/^[\p{L}\p{N}_.\- /]*$/u.test(sf) || sf.includes(".."))
      errors.push("app_settings.selective_sync_folder must be a folder inside the project");
    const names = new Set((spec.layers || []).map((l) => l && l.name));
    for (const f of app.filters || []) {
      if (!f || typeof f !== "object" || !f.layer || !f.field) errors.push("each filter needs 'layer' and 'field'");
      else if (mode === "new" && !names.has(f.layer)) errors.push(`filter: no layer called "${f.layer}" in this spec`);
    }
    if (mode === "new" && !(spec.layers || []).length) errors.push("a new project needs at least one layer");
    for (const layer of spec.layers || []) {
      if (layer && "color" in layer && !/^#[0-9a-fA-F]{6}$/.test(String(layer.color)))
        errors.push(`${layer.name}: color must look like #1db278`);
    }
    const aoi = (spec.area_of_interest || {}).bbox;
    if (aoi !== undefined && aoi !== null && !(Array.isArray(aoi) && aoi.length === 4 && aoi.every(isNum)
        && -180 <= aoi[0] && aoi[0] < aoi[2] && aoi[2] <= 180 && -90 <= aoi[1] && aoi[1] < aoi[3] && aoi[3] <= 90))
      errors.push("area_of_interest.bbox must be [west, south, east, north] in degrees");
  }

  // ---------- render.py: check_spec ----------
  function checkSpec(spec, errors, warnings) {
    const lists = spec.lookup_lists || {};
    for (const name of Object.keys(lists)) {
      if (!NAME.test(name) || RESERVED_PREFIX.test(name))
        errors.push(`lookup list '${name}': use lowercase letters, numbers and _`);
      if (!Array.isArray(lists[name]) || !lists[name].every((v) => typeof v === "string" && v))
        errors.push(`lookup list '${name}': values must be non-empty text`);
    }
    const layers = Array.isArray(spec.layers) ? spec.layers : [];
    const all = layers.map((l) => (l && l.name) || "?").concat(Object.keys(lists))
      .concat(layers.filter((l) => l && l.multiple_photos).map((l) => (l.name || "?") + "_photos"));
    if (all.length !== new Set(all).size) errors.push("two layers / lookup lists / photo tables share a name");
    for (const layer of layers) {
      if (!layer || typeof layer !== "object") { errors.push("a layer is not an object"); continue; }
      const missing = ["name", "geometry", "fields"].filter((k) => !(k in layer));
      if (missing.length) { errors.push(`a layer is missing ${missing.join(", ")}`); continue; }
      if (!NAME.test(layer.name) || RESERVED_PREFIX.test(layer.name))
        errors.push(`layer '${layer.name}': use lowercase letters, numbers and _ (not gpkg_/rtree_/sqlite_)`);
      if (!Array.isArray(layer.fields) || layer.fields.some((f) => !f || !("name" in f) || !("type" in f))) {
        errors.push(`${layer.name}: every field needs a 'name' and a 'type'`); continue;
      }
      if (!["point", "line", "polygon", "none"].includes(layer.geometry))
        errors.push(`${layer.name}: geometry must be point, line, polygon or none`);
      const names = layer.fields.map((f) => f.name);
      if (layer.title && !names.concat(["uuid"]).includes(layer.title))
        errors.push(`${layer.name}: title '${layer.title}' is not one of its fields`);
      for (const f of layer.fields) {
        const where = `${layer.name}.${f.name}`;
        const widget = f.widget ?? "text";
        if (!TYPES.includes(f.type)) errors.push(`${where}: type must be one of ${TYPES.join(", ")}`);
        if (!NAME.test(f.name)) errors.push(`${where}: use lowercase letters, numbers and _`);
        if (AUTOMATIC.has(f.name) || String(f.name).startsWith("spare_")) errors.push(`${where}: name is reserved for an automatic field`);
        if (!(widget in WIDGET_TYPES)) errors.push(`${where}: unknown widget '${widget}'`);
        else if (WIDGET_TYPES[widget] && !WIDGET_TYPES[widget].includes(f.type))
          errors.push(`${where}: widget '${widget}' needs type ${WIDGET_TYPES[widget].join(" or ")}`);
        if ("min" in f && "max" in f && f.min > f.max) errors.push(`${where}: min is bigger than max`);
        if (widget === "hidden" && f.required && !f.default)
          errors.push(`${where}: a hidden required field with no default can never be filled`);
        if (widget === "number" && (!("min" in f) || !("max" in f)))
          warnings.push(`${where}: number without min/max (sliders break: mobile#1516). Add both.`);
        if (f.default && /"[a-z]/.test(String(f.default)))
          warnings.push(`${where}: default refers to another field; may not apply on new features (mobile#4417)`);
        if (widget === "dropdown" && !(Array.isArray(f.choices) && f.choices.length)) errors.push(`${where}: dropdown needs choices`);
        const rule = f.constraint;
        if (rule !== undefined && rule !== null && !(typeof rule === "object" && rule.expression))
          errors.push(`${where}: constraint needs an 'expression' (and a 'message')`);
        else if (rule && !rule.message) errors.push(`${where}: constraint needs a 'message' to show in the app`);
        if (widget === "lookup" && !(f.list in lists)) errors.push(`${where}: lookup list '${f.list}' is not in lookup_lists`);
      }
      if (names.length !== new Set(names).size) errors.push(`${layer.name}: duplicate field names`);
      const visible = layer.fields.filter((f) => (f.widget ?? "text") !== "hidden");
      for (const f of visible) {
        for (const key of ["tab", "group"]) {
          if (key in f && !(typeof f[key] === "string" && f[key].trim().length > 0 && f[key].trim().length <= 40))
            errors.push(`${layer.name}.${f.name}: ${key} must be a short name (1-40 characters)`);
        }
      }
      const tabbed = visible.filter((f) => f.tab);
      if (tabbed.length && tabbed.length !== visible.length)
        errors.push(`${layer.name}: some fields have a tab, these don't: ${visible.filter((f) => !f.tab).map((f) => f.name).join(", ")}`);
      if (layer.multiple_photos) {
        if (layer.geometry === "none") errors.push(`${layer.name}: multiple_photos needs a map layer (point/line/polygon)`);
        if (layer.fields.some((f) => f.widget === "photo"))
          warnings.push(`${layer.name}: has a single photo field AND multiple_photos; the app can overwrite the single photo with gallery photos (mobile#2029). Use only one.`);
      }
    }
  }

  function check(spec) {
    const errors = [], warnings = [];
    if (!spec || typeof spec !== "object" || Array.isArray(spec)) return { errors: ["The spec is not a JSON object"], warnings };
    try {
      checkSettings(spec, errors, warnings);
      checkSpec(spec, errors, warnings);
    } catch (e) {
      errors.push("The spec has an unexpected shape: " + e.message);
    }
    return { errors, warnings };
  }

  // ---------- render.py: aliases ----------
  const ALIAS_UNITS = { m: "m", cm: "cm", mm: "mm", km: "km", ft: "ft", in: "in", mi: "mi", m2: "m²", ha: "ha", ac: "acres",
    deg: "°", pct: "%", percent: "%", kg: "kg", g: "g", lb: "lb", c: "°C", f: "°F", ms: "m/s", l: "L" };
  const ALIAS_WORDS = { id: "ID", gps: "GPS", dbh: "DBH", uuid: "UUID", url: "URL", gis: "GIS", qa: "QA", qc: "QC", ph: "pH", no: "number" };

  function defaultAlias(field) {
    let words = String(field.name).split("_");
    let unit = "";
    if (words.length > 1 && words[words.length - 1] in ALIAS_UNITS) unit = ` (${ALIAS_UNITS[words.pop()]})`;
    const firstSpecial = words[0] in ALIAS_WORDS;
    words = words.map((w) => ALIAS_WORDS[w] || w);
    let label = words.join(" ");
    if (!firstSpecial) label = label.slice(0, 1).toUpperCase() + label.slice(1);
    if (field.widget === "checkbox" && !label.endsWith("?")) label += "?";
    return label + unit;
  }

  function fillAliases(spec) {
    for (const layer of spec.layers || []) {
      for (const f of layer.fields || []) {
        if (!f.alias && (f.widget ?? "text") !== "hidden") f.alias = defaultAlias(f);
      }
    }
    return spec;
  }

  // ---------- preview.py ----------
  const TYPE = { text: "text", integer: "integer", decimal: "decimal", date: "date", datetime: "date+time", boolean: "yes/no" };
  const QUALITY = { 0: "original", 1: "high", 2: "medium", 3: "low" };
  const SNAP = { 0: "off", 1: "basic", 2: "follow QGIS" };
  const FREQ = { 0: "best", 1: "normal", 2: "low" };
  const short = (items, limit = 4) => {
    items = (items || []).map(String);
    return items.slice(0, limit).join(" · ") + (items.length > limit ? ` · +${items.length - limit}` : "");
  };
  function lean(expression, limit = 70) {
    const m = /^\s*(\S+) IS NULL OR \(?(.*?)\)?\s*$/.exec(expression);
    const text = m ? `${m[2]}  (empty is ok)` : expression;
    return text.length <= limit ? text : text.slice(0, limit - 1) + "…";
  }
  function numberRange(f) {
    const lo = f.min, hi = f.max;
    if (lo == null && hi == null) return "number";
    return `number ${lo == null ? "" : lo}–${hi == null ? "" : hi}`;
  }
  function inputOf(f, lists) {
    const w = f.widget ?? "text";
    if (w === "dropdown") return "pick: " + short(f.choices);
    if (w === "lookup") {
      const values = lists[f.list] || [];
      return `${f.multiple ? "pick many" : "pick"} from ${f.list} (${values.length}, editable)`;
    }
    if (w === "number") return numberRange(f);
    return { text: "typed", notes: "typed, multi-line", checkbox: "switch", date: "calendar",
      photo: "photo (camera/gallery)" }[w] || w;
  }
  function formOrder(fields) {
    const tabs = new Map();
    for (const f of fields) {
      const k = f.tab ?? null;
      if (!tabs.has(k)) tabs.set(k, []);
      tabs.get(k).push(f);
    }
    const ordered = [];
    for (const tabFields of tabs.values()) {
      const slots = new Map();
      for (const f of tabFields) {
        const key = f.group ? "g:" + f.group : "f:" + f.name;
        if (!slots.has(key)) slots.set(key, []);
        slots.get(key).push(f);
      }
      for (const slot of slots.values()) ordered.push(...slot);
    }
    return ordered;
  }
  const pad = (s, n) => s + " ".repeat(Math.max(0, n - [...s].length));
  function layerBlock(layer, lists, out) {
    const fields = layer.fields || [];
    const visible = fields.filter((f) => (f.widget ?? "text") !== "hidden");
    const hidden = fields.filter((f) => (f.widget ?? "text") === "hidden");
    const tf = fields.find((f) => f.name === layer.title);
    const title = tf ? tf.alias || defaultAlias(tf) : null;
    const head = [layer.geometry];
    if (title) head.push(`title: ${title}`);
    if (layer.multiple_photos) head.push("photo gallery");
    out.push(`${String(layer.name).toUpperCase()}  ${head.join(" · ")}`);
    const rows = formOrder(visible).map((f) => [
      (f.alias || defaultAlias(f)) + (f.required ? " *" : ""), f.name, TYPE[f.type] || f.type, inputOf(f, lists), f]);
    const w = [0, 1, 2].map((i) => Math.max(0, ...rows.map((r) => [...r[i]].length)));
    let where = [undefined, undefined];
    for (const [label, name, kind, how, f] of rows) {
      if ((f.tab ?? null) !== where[0] || (f.group ?? null) !== where[1]) {
        if (f.tab && f.tab !== where[0]) out.push(`  [ ${f.tab} ]`);
        if (f.group) out.push(`  ── ${f.group}`);
        where = [f.tab ?? null, f.group ?? null];
      }
      out.push(`  ${pad(label, w[0])}  ${pad(name, w[1])}  ${pad(kind, w[2])}  ${how}`);
      const p = " ".repeat(w[0] + 4);
      if (f.default) out.push(`${p}= ${f.default}${f.update ? ", on every edit" : ""}`);
      const rule = f.constraint;
      if (rule) {
        out.push(`${p}✓ "${rule.message || ""}"  ${rule.hard === false ? "warning only" : "blocks saving"}`);
        out.push(`${p}  unless: ${lean(rule.expression)}`);
      }
    }
    const auto = ["uuid", "created/updated at·by"].concat(layer.geometry === "point" ? ["GPS accuracy"] : []);
    let line = "  ┄ hidden, filled by the app: " + auto.join(" · ") + " · 5 spare fields";
    if (hidden.length) line += " · also hidden: " + hidden.map((f) => f.name).join(", ");
    out.push(line);
    if (layer.multiple_photos) out.push(`  ┄ ${layer.name}_photos: Photo · Caption, one row per photo, linked by uuid`);
    out.push("");
  }
  function previewText(spec) {
    const lists = spec.lookup_lists || {};
    const app = appSettings(spec);
    const out = [];
    const mode = spec.mode ?? "new";
    const bgKey = spec.background === undefined ? "mergin" : spec.background;
    const bg = { mergin: "Mergin Maps tiles", osm: "OpenStreetMap" }[bgKey] || (bgKey === null ? "no background" : bgKey);
    const where = (spec.area_of_interest || {}).label;
    const project = [spec.project_name, mode === "new" ? "new project" : "add to existing"];
    if (mode === "new") project.push(spec.crs || "EPSG:4326");
    else if ((spec.layers || []).length) project.push(`new layers in ${spec.crs || "EPSG:4326"}`);
    if (spec.qgis_version) project.push(`QGIS ${spec.qgis_version}`);
    if (mode === "new") { project.push(bg); if (where) project.push(where); }
    out.push("PROJECT  " + project.join(" · "));
    const s = [];
    if ("photo_quality" in app || mode === "new") s.push(`photos ${QUALITY[app.photo_quality ?? 1]}`);
    if ("snapping" in app || mode === "new") s.push(`snapping ${SNAP[app.snapping ?? 0]}`);
    if (app.position_tracking) s.push(`tracking ${FREQ[app.tracking_frequency ?? 1] || "normal"}`);
    const sketch = [["map_sketching", "map"], ["photo_sketching", "photo"]].filter(([k]) => app[k]).map(([, n]) => n);
    if (sketch.length) s.push("sketching " + sketch.join("+"));
    if (app.layer_order === "alphabetical") s.push("layers A–Z");
    if (app.selective_sync) s.push(`selective sync ${app.selective_sync_folder || "photos"}/`);
    if ((app.filters || []).length) s.push("filters: " + app.filters.map((f) => f.name || `${f.layer}.${f.field}`).join(", "));
    if (s.length) out.push("APP      " + s.join(" · "));
    for (const [name, values] of Object.entries(lists)) out.push(`LIST     ${name} (${values.length}): ${short(values)}`);
    out.push("");
    for (const layer of spec.layers || []) layerBlock(layer, lists, out);
    if (!(spec.layers || []).length) out.push("(no new layers: only the settings above change)");
    out.push("* required · = filled in automatically · ✓ message shown in the app");
    return out.join("\n").replace(/\s+$/, "");
  }

  // ---------- render.py: Python literals ----------
  // JSON string escapes (\" \\ \n \t \uXXXX) are all valid in Python strings.
  function pyInline(v) {
    if (v === null || v === undefined) return "None";
    if (v === true) return "True";
    if (v === false) return "False";
    if (typeof v === "number") return Number.isFinite(v) ? String(v) : "None";
    if (typeof v === "string") return JSON.stringify(v);
    if (Array.isArray(v)) return "[" + v.map(pyInline).join(", ") + "]";
    return "{" + Object.entries(v).map(([k, x]) => JSON.stringify(k) + ": " + pyInline(x)).join(", ") + "}";
  }
  function py(v, ind = 0) {
    const one = pyInline(v);
    if (v === null || typeof v !== "object" || one.length + ind <= 96) return one;
    const inner = " ".repeat(ind + 4), end = " ".repeat(ind);
    if (Array.isArray(v)) {
      if (!v.length) return "[]";
      return "[\n" + v.map((x) => inner + py(x, ind + 4)).join(",\n") + ",\n" + end + "]";
    }
    const entries = Object.entries(v);
    if (!entries.length) return "{}";
    return "{\n" + entries.map(([k, x]) => inner + JSON.stringify(k) + ": " + py(x, ind + 4)).join(",\n") + ",\n" + end + "}";
  }
  const pyRepr = (v) => (v === undefined ? "None" : pyInline(v));
  const plain = (t) => String(t).replace(/["\\\n\r]/g, "").slice(0, 80);
  function today() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  // ---------- render.py: main ----------
  function renderScript(specIn, template) {
    const spec = fillAliases(JSON.parse(JSON.stringify(specIn)));
    const { errors } = check(spec);
    if (errors.length) throw new Error("Spec problems:\n  - " + errors.join("\n  - "));
    const aoi = spec.area_of_interest;
    const app = appSettings(spec);
    const values = {
      PROJECT_TITLE: plain(spec.title || spec.project_name),
      MODE: spec.mode || "new",
      PROJECT_NAME: spec.project_name,
      PARENT_FOLDER: spec.parent_folder || "MerginMaps Projects",
      CRS: spec.crs || "EPSG:4326",
      AREA_OF_INTEREST: aoi && aoi.bbox ? py(aoi.bbox) + `  # ${plain(aoi.label || "")}` : "None",
      BACKGROUND: String(spec.background === undefined ? "mergin" : spec.background),
      PHOTO_QUALITY: pyRepr(app.photo_quality),
      SNAPPING: pyRepr(app.snapping),
      POSITION_TRACKING: pyRepr(app.position_tracking),
      TRACKING_FREQUENCY: pyRepr(app.tracking_frequency),
      MAP_SKETCHING: pyRepr(app.map_sketching),
      SKETCH_COLORS: pyRepr(app.sketch_colors),
      PHOTO_SKETCHING: pyRepr(app.photo_sketching),
      LAYER_ORDER: pyRepr(app.layer_order),
      SELECTIVE_SYNC: pyRepr(app.selective_sync),
      SELECTIVE_SYNC_FOLDER: pyRepr(app.selective_sync_folder ?? "photos"),
      FILTERS: py(app.filters || []),
      LOOKUP_LISTS: py(spec.lookup_lists || {}),
      LAYERS: py(spec.layers || []),
      QGIS_VERSION: String(spec.qgis_version || "3.x"),
      DATE: today(),
    };
    let text = template;
    if (spec.background === null) text = text.replace('"{{BACKGROUND}}"', "None");
    const unknown = [...text.matchAll(/\{\{([A-Z_]+)\}\}/g)].map((m) => m[1]).filter((k) => !(k in values));
    if (unknown.length) throw new Error("Template placeholders without a value: " + unknown.join(", "));
    return text.replace(/\{\{([A-Z_]+)\}\}/g, (_, k) => values[k]);
  }

  // ---------- form_preview.py ----------
  const scriptJson = (v) => JSON.stringify(v).replace(/<\//g, "<\\/").replace(/<!--/g, "<\\!--");
  function formPreviewHtml(specIn, page, fontBase64, icons) {
    const spec = fillAliases(JSON.parse(JSON.stringify(specIn)));
    const values = { FONT: fontBase64, SPEC: scriptJson(spec), ICONS: scriptJson(icons) };
    return page.replace(/\{\{([A-Z]+)\}\}/g, (m, k) => (k in values ? values[k] : m));
  }

  // ---------- known bugs that affect a design (checked 2026-11-03) ----------
  function bugNotes(spec) {
    const app = appSettings(spec);
    const layers = spec.layers || [];
    const fields = layers.flatMap((l) => l.fields || []);
    const notes = [];
    const add = (id, text) => notes.push({ id, text, url: "https://github.com/MerginMaps/mobile/issues/" + id.split("#")[1] });
    if (app.position_tracking) {
      add("mobile#3555", "The app can crash when a surveyor stops tracking. The data is kept; they reopen the app.");
      add("mobile#4588", "On Android, tracking stops while the screen is off. Keep the screen on while tracking.");
      add("mobile#4315", "A track can be lost if the app is closed during tracking. Don't close the app mid-route.");
    }
    if (layers.some((l) => l.multiple_photos && (l.fields || []).some((f) => f.constraint || f.required)))
      add("mobile#1692", "A rule on one field may affect the whole form on layers with a photo gallery. Test it on a phone.");
    if (layers.some((l) => l.multiple_photos && (l.fields || []).some((f) => f.widget === "photo")))
      add("mobile#2029", "Gallery photos can overwrite a single photo field on the same layer. Use one or the other.");
    const multi = new Set(layers.flatMap((l) => (l.fields || []).filter((f) => f.multiple).map((f) => l.name + "." + f.name)));
    if ((app.filters || []).some((f) => multi.has(f.layer + "." + f.field)))
      add("mobile#4574", "Filtering on a pick-several field can count features wrongly when several values are picked.");
    if (app.selective_sync)
      add("mobile#4060", "Turning selective sync on or off mid-survey can leave phones 'pending'. It's set now, at creation; keep it that way.");
    if (fields.some((f) => f.widget === "lookup"))
      add("mobile#4053", "Don't turn on 'Reuse last value' for lookup fields; it misbehaves there.");
    return notes;
  }

  const api = { check, appSettings, defaultAlias, fillAliases, previewText, renderScript, formPreviewHtml, bugNotes, py };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MMB = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
