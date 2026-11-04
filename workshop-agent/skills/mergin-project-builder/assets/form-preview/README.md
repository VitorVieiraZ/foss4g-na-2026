# Form preview assets

Used by `scripts/form_preview.py` to build a self-contained web page that
looks like a feature form in the Mergin Maps mobile app.

- `app.html`: the page template (HTML, CSS, JS). `{{FONT}}`, `{{SPEC}}` and
  `{{ICONS}}` are filled in by the script.
- `icons/`: SVG icons copied from the Mergin Maps mobile app
  (github.com/MerginMaps/mobile, `app/icons`, GPL-2.0), commit 4557df6.
  The script recolours them with `currentColor`, as the app tints them.
- `inter-latin.woff2`: Inter (SIL Open Font License), the app's font.

Colours, sizes and messages follow `app/mmstyle.h`, `app/qml/form/` and
`app/attributes/fieldvalidator.cpp` at the same commit. If the app's look
changes, update the `:root` colours and component sizes in `app.html`.
