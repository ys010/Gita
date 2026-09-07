#!/usr/bin/env python3
"""
scraper.py — pulls the Bhagavad Gita (Swami Sivananda's translation and
commentary) from dlshq.org and writes data/chapter-01.json .. chapter-18.json
in the schema index.html reads.

Run this yourself, once, from your own machine (this sandbox's network
policy blocks dlshq.org, so it can't be run from inside a Claude Code
session — see scraper_github_dataset.py for a scraper that *can* run here,
sourced from a mirror on GitHub instead):

    pip install requests beautifulsoup4
    python scraper.py

Re-run any time to refresh (e.g. if the source page is corrected/updated).
This script contains no scripture text itself — it only fetches and parses
the public page at runtime, when you run it.
"""

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.dlshq.org/download/bhagavad-gita/"
OUT_DIR = Path(__file__).parent / "data"

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
    "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18,
}

VERSE_NUM_RE = re.compile(r"^(\d+(?:[-–]\d+)?)\.\s*(.*)$", re.S)
COMMENTARY_RE = re.compile(r"^\*{0,2}COMMENTARY:?\*{0,2}\s*(.*)$", re.S | re.I)
SPEAKER_RE = re.compile(r"^\s*(.+?)\s+Uvaach\w*\s*:?\s*$", re.I)


def is_italic_only(p_tag):
    """True if a <p> tag's visible text is entirely inside <em>/<i> children."""
    text = p_tag.get_text(strip=True)
    if not text:
        return False
    italic_text = "".join(t.get_text() for t in p_tag.find_all(["em", "i"]))
    return len(italic_text.strip()) >= len(text) * 0.8  # tolerant match


def fetch_soup():
    resp = requests.get(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0 (personal study tool)"}, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse(soup):
    """
    Walk the page in document order. Chapters are marked by an <h2> whose
    text is a bare roman numeral (I..XVIII), immediately followed by an
    <h2> with the English chapter title. Verses are recognised as:
      - one or more consecutive italic-only <p> = Sanskrit lines (the first
        of two such lines is a speaker tag, e.g. "Arjuna Uvaacha:")
      - the next non-italic <p> starting "N. " or "N-M. " = translation
      - an optional following <p> starting "COMMENTARY:" = commentary
    Verse numbers like "21-22" (two verses translated as one continuous
    passage) are expanded into individual verse records with the same
    text, tagged with a shared verse_label, so every chapter still counts
    up one verse number at a time.
    """
    chapters = {}
    current_chapter = None
    pending_sanskrit = []
    expect_title_next = False

    body_tags = soup.find_all(["h2", "h3", "p"])

    for tag in body_tags:
        text = tag.get_text(" ", strip=True)
        if not text:
            continue

        if tag.name == "h2":
            roman = text.strip().upper()
            if roman in ROMAN_TO_INT:
                current_chapter = ROMAN_TO_INT[roman]
                chapters[current_chapter] = {"chapter": current_chapter, "title": None, "raw_verses": []}
                expect_title_next = True
                pending_sanskrit = []
                continue
            if expect_title_next and current_chapter is not None:
                chapters[current_chapter]["title"] = text
                expect_title_next = False
                continue
            continue

        if current_chapter is None:
            continue  # front matter (prayers, prefaces) — skipped on purpose

        if tag.name == "p":
            m_comment = COMMENTARY_RE.match(text)
            if m_comment and chapters[current_chapter]["raw_verses"]:
                chapters[current_chapter]["raw_verses"][-1]["commentary"] = m_comment.group(1).strip()
                continue

            m_verse = VERSE_NUM_RE.match(text)
            if m_verse:
                chapters[current_chapter]["raw_verses"].append({
                    "number": m_verse.group(1),
                    "sanskrit": pending_sanskrit,
                    "translation": m_verse.group(2).strip(),
                })
                pending_sanskrit = []
                continue

            if is_italic_only(tag):
                pending_sanskrit.append(text)
                continue

            # anything else (chapter summaries, closing verses of each
            # discourse) is intentionally skipped — this scraper only
            # keeps numbered verses + their commentary.

    return chapters


def split_speaker(lines):
    """A verse's italic lines are either [verse] or [speaker tag, verse]."""
    if len(lines) == 2:
        m = SPEAKER_RE.match(lines[0])
        speaker = m.group(1).strip() if m else lines[0].strip().rstrip(":").strip()
        return speaker, lines[1]
    return "", lines[0] if lines else ""


def expand_verse_number(number):
    """'21-22' -> ([21, 22], '21-22'); '5' -> ([5], None)."""
    if "-" in number:
        a, b = number.split("-", 1)
        return list(range(int(a), int(b) + 1)), number
    return [int(number)], None


def build_chapter_record(chapter_num, raw):
    verses = []
    for v in raw["raw_verses"]:
        speaker, sanskrit = split_speaker(v["sanskrit"])
        verse_nums, label = expand_verse_number(v["number"])
        commentary = (v.get("commentary") or "").strip()
        for vn in verse_nums:
            verses.append({
                "chapter": chapter_num,
                "verse": vn,
                "verse_label": label,
                "speaker": speaker,
                "sanskrit": sanskrit,
                "translation": v["translation"].strip(),
                "commentary": commentary,
                "commentary_author": "Swami Sivananda" if commentary else "",
            })
    verses.sort(key=lambda x: x["verse"])
    return {
        "chapter": chapter_num,
        "title_sanskrit": "",
        "title_transliteration": "",
        "title_translation": raw.get("title") or "",
        "summary": "",
        "verse_count": len(verses),
        "verses": verses,
    }


def main():
    print(f"Fetching {SOURCE_URL} ...")
    soup = fetch_soup()
    print("Parsing ...")
    chapters = parse(soup)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_verses = 0
    for n in range(1, 19):
        raw = chapters.get(n)
        if not raw or not raw["raw_verses"]:
            print(f"  ! chapter {n}: nothing parsed — check the source page structure "
                  f"or adjust the selectors in parse()", file=sys.stderr)
            continue
        record = build_chapter_record(n, raw)
        out_path = OUT_DIR / f"chapter-{n:02d}.json"
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        total_verses += record["verse_count"]
        print(f"  chapter {n:2d}: {record['title_translation']!r} — {record['verse_count']} verses -> {out_path.name}")

    print(f"\nDone. {total_verses} verses written to {OUT_DIR}/")
    if total_verses < 650:
        print("Note: the traditional count is 700 verses — if you're well under that, "
              "the parser likely missed some verses due to page-formatting quirks. "
              "Re-check parse() against the actual page HTML.", file=sys.stderr)


if __name__ == "__main__":
    main()
