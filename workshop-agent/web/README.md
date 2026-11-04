# Project Builder (web)

The Mergin Maps project builder agent as one web page: **Describe → Review form → Get script**.
Published privately at https://claude.ai/artifact/8CiC6mW792yXoExtf1pxks.

- `index.html`: the page. Claude turns the description into a spec (artifact `sample`
  capability, on the viewer's own Claude account); the page offers files through `downloads`.
- `core.js`: browser ports of the skill's `render.py` checks and script rendering,
  `preview.py` and `form_preview.py`. Keep them in step with the Python scripts.
- `icons.json`: the app icons, made with `form_preview.icons()`.

The skill's own files are published next to the page, unchanged:
`tpl/app.html.txt` (form preview), `tpl/build_project.txt` (script template),
`tpl/inter-latin.woff2`.

Downloads can't be `.py` files, so the script comes in a `.zip` (script, spec,
form preview, README), or through the Copy button.

To check the port after changing the skill (macOS, no Node needed), render the same spec
with `jsc core.js` and with `render.py`/`preview.py`, then diff: the preview text and
every SECTION 1 value must match, and the script must pass `python3 -m py_compile`.
