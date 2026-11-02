# FOSS4G NA 2026 · Mergin Maps (Vitor Vieira, Lutra Consulting)

Talk + workshop for FOSS4G North America 2026, Sacramento. Vitor works at Lutra (makes Mergin Maps); offers and wording are his to approve.

## What's here
- `mergin-deck/index.html` — the **talk** deck (HTML, 24 slides). Published privately at https://claude.ai/artifact/FybxYi15PM7rzFoEPRzz7F — republish from this file.
- `mergin-deck/assets/` — all images, `demo.mp4` (slide 8), `qr-offer.png` (form QR), `orgs/` logos, `crew-*.jpg` collage photos.
- `form-auto-email.gs` — Apps Script that emails form sign-ups (NOT installed, see Form below).
- `Video FOSS4G NA.mp4` — source of the demo video (2:42, QGIS → phone → QGIS → web map). Same as https://youtu.be/YC1hjQ_dNjc.
- Original Google Slides: "Mergin Maps — FOSS4G NA 2026" (Drive id 1cLX06m8nOsD4HQeepTS-DqXcfpkS0hEiIMiDsLaOMjo).
- Workshop source deck: `~/Downloads/_MAIN FOSS4GNA 2026 Workshop_ From QGIS to the Field and Back with Mergin Maps.pptx` (7 slides).

## Content rules (agreed)
- **Very little text.** Model: a talk where the speaker carries it. Title (often a two-part line) + at most 2–3 short points + one visual. Long text goes into speaker notes (`data-notes` on the slide; **N** key toggles them).
- **Core message:** Mergin Maps makes field data **consistent and reliable over the years**.
- **Audience:** American — state impact plainly. But FOSS4G is an open-source conference: **never pitch** or sell; no pricing on slides.
- Wording decisions: "External GPS" (not GNSS); name **ArcGIS** in the BGS story; case studies get a factual **Result** line from real figures; no invented customers/logos (merginmaps.com has no US case studies).
- Closing question: **"Are you surveying the best way you can?"** (same question opens the talk).
- Joke slide: "You Can Survey Everything" — title + image only, riffing on a "You Can Code Everything" slide.

## Design system (keep exactly — don't restyle unless asked)
- 1920×1080 stage scaled to the window; side margins 144px; titles at 132px from top.
- Font: Inter. Colors: ink `#0e3b31`, accent `#1db278`, mist `#eef3ef` (default bg), paper `#fbfcfb`, text `#3a4a44`, warn `#c2410c`, peach `#f6a463`.
- Slide classes: default (mist), `.paper`, `.dark` (ink bg, light text), `.photo`. **These three rules must exist**: `.slide.paper`, `.slide.dark`, `.slide.photo` — they were once deleted by accident and the user noticed immediately.
- Mergin Maps app UI colors (sampled from screen recordings): bar `#00423c`, mint `#66c68f`, feature red `#e1312d`, GPS pill `#f4d6a3`, app text `#273b36`, orange polygons `#ffad42`.

## Transitions (in the deck's script)
- Seven field-work transitions drawn in Mergin Maps app UI, mapped per slide in `KIND`: gps (position marker + accuracy pill + red feature point, route grows per "chapter"), contour, polygon (record mode + "Add point"), sync (app bottom bar), tiles (web map + scale bar), photo (viewfinder, soft flash), measure (crosshair + Length chip).
- A "field log" chip tells one survey day in Sacramento (`STORY` array; case studies cut to UK/Canada). Last slide replays the day's route.
- User wants them **soft and minimal** at normal speed (`SPEED = 1`).
- Video slide: first "next" plays the video, next "next" advances.

## Form + follow-up
- Google Form (owned by personal account vitormouravieira@yahoo.com.br, Lutra account vitor.vieira@lutraconsulting.co.uk is Editor): https://forms.gle/PK44BeoB4jZKBTpVA — Email (required), Organization, How will you use Mergin Maps? Offer: **1-month free trial**.
- Auto-email via Apps Script is **blocked**: Lutra's Workspace returns `Error 401: invalid_client` when authorizing. Needs the Workspace admin to allow Apps Script, or fall back to a same-day BCC email from Lutra Gmail. Register link: https://app.merginmaps.com/register.

## Lessons from building the talk
- Edit HTML with exact, unique replacements and diff styles/script against a backup afterwards; never replace a large region without checking what else is in it.
- Preview pane renders late: wait several seconds before screenshots, or freeze animations with `document.getAnimations()`.
- Artifact images: a global `#stage img{max-width:none}` rule overrides class rules — use `#stage .x img` for limits.
