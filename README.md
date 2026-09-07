# Gita

A single-page, dark and warm reader for the Bhagavad Gita — Sanskrit verse,
translation and commentary for all 701 verses across its 18 chapters, read
one small daily passage at a time.

**[Read it live →](#)** *(see GitHub Pages setup below)*

## What's here

- `scraper.py` — fetches Swami Sivananda's translation and commentary from
  [dlshq.org](https://www.dlshq.org/download/bhagavad-gita/) and writes
  `data/chapter-01.json` … `chapter-18.json`, the schema `index.html` reads.
  **Must be run from a machine with normal internet access** — see below.
- `scraper_github_dataset.py` — an alternate scraper, sourced from the
  [vedicscriptures/bhagavad-gita](https://github.com/vedicscriptures/bhagavad-gita)
  dataset (Prabhupada's translation, plus real Devanagari script and
  transliteration, which the dlshq source doesn't have). Not currently
  used by the live reader, but kept because it's the one scraper here that
  *can* run inside a sandboxed Claude Code session — dlshq.org and every
  other Gita site tried is blocked by such sandboxes' network policy, but
  raw.githubusercontent.com generally isn't.
- `data/` — the scraped output that feeds the reader, one JSON file per chapter.
- `index.html` — the reader itself: a single static HTML file with vanilla
  JS, no build step, no framework.

## Running the scraper

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scraper.py
```

This needs a normal internet connection to reach dlshq.org — it won't run
inside a network-restricted sandbox. Re-run any time to refresh (e.g. if
the source page is corrected). Console output shows a per-chapter verse
count and flags anything that parsed to zero verses.

Note on verse count: the traditional count of 700 verses is a round
figure. This edition numbers to 701 because chapter 1, verses 21 and 22,
are one continuous sentence traditionally translated (and counted) as a
single passage but still numbered individually — the reader shows both
numbers on that one entry (`1.21-22`) and steps through them as two verses.

## Reading the app

`index.html` reads the `data/chapter-*.json` files with `fetch()`, so it
needs to be served over HTTP — opening the file directly (`file://`) will
be blocked by the browser's CORS rules. Locally:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

The reader shows one full chapter at a time, scrollable — not a fixed
daily batch. Each verse has its own "mark as here" button; clicking one
sets your bookmark to exactly that verse, so you place it wherever you
actually stopped reading. Your reading position is saved in your
browser's `localStorage` under the key `gita-bookmark`, as
`{chapter, verse}` — nothing is sent anywhere. The progress bar and
chapter ticks always reflect that saved bookmark, even while you're
looking at a different chapter; a "jump to my place" button snaps back
and scrolls to it.

Note: dlshq.org's source page gives each verse in Romanized/IAST-style
Sanskrit only (e.g. `Dharmakshetre kurukshetre...`), not Devanagari
script — that's what's shown as the verse text. `scraper_github_dataset.py`
is the one that produces real Devanagari, if you switch sources (see above).

## GitHub Pages

Once this repo is on GitHub: **Settings → Pages → Build and deployment →
Source: Deploy from a branch → Branch: `main` / `(root)` → Save.** The
site will then be live at `https://<owner>.github.io/<repo>/`.
