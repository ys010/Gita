# Gita

A single-page, dark and warm reader for the Bhagavad Gita — Sanskrit,
transliteration, translation and commentary for all 701 verses across its
18 chapters, read one small daily passage at a time.

**[Read it live →](#)** *(see GitHub Pages setup below)*

## What's here

- `scraper.py` — fetches the verse-by-verse data (Sanskrit, transliteration,
  translation, commentary) and writes `data/chapter-01.json` … `chapter-18.json`.
- `data/` — the scraped output, one JSON file per chapter.
- `index.html` — the reader itself: a single static HTML file with vanilla
  JS, no build step, no framework.

## Running the scraper

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scraper.py
```

Source data: the open [vedicscriptures/bhagavad-gita](https://github.com/vedicscriptures/bhagavad-gita)
dataset (GPLv3), which itself compiles well-known public translations and
commentaries (Prabhupada, Sivananda, and others). For each verse the
scraper walks a fixed chain of commentators and keeps the first one with
both a translation and a commentary.

Note on verse count: the traditional count of 700 verses is a round
figure; chapter 13 has a well-known textual variant that puts the total
at 701 verses in most modern editions, this one included.

## Reading the app

`index.html` reads the `data/chapter-*.json` files with `fetch()`, so it
needs to be served over HTTP — opening the file directly (`file://`) will
be blocked by the browser's CORS rules. Locally:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

Your reading position is saved in your browser's `localStorage` under the
key `gita-bookmark`, as `{chapter, verse, pace}` — nothing is sent
anywhere. "Mark read & continue" advances the bookmark by `pace` verses
(default 5/day); the progress bar and chapter ticks always reflect that
saved bookmark, even while you're browsing elsewhere in the text.

## GitHub Pages

Once this repo is on GitHub: **Settings → Pages → Build and deployment →
Source: Deploy from a branch → Branch: `main` / `(root)` → Save.** The
site will then be live at `https://<owner>.github.io/<repo>/`.
