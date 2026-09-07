#!/usr/bin/env python3
"""
scraper_dlshq.py — pulls the Bhagavad Gita (Sivananda translation + commentary)
from dlshq.org into per-chapter JSON files under ./data_dlshq/

Run this yourself, once, from your own machine (this sandbox's network
policy blocks dlshq.org, so it can't be run from inside the Claude session):

    pip install requests beautifulsoup4
    python scraper_dlshq.py

It writes data_dlshq/chapter-01.json ... data_dlshq/chapter-18.json.
Re-run any time to refresh (e.g. if the source page is corrected/updated).

This script contains no scripture text itself — it only fetches and
parses the public page at runtime, when you run it.
"""

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.dlshq.org/download/bhagavad-gita/"
OUT_DIR = Path(__file__).parent / "data_dlshq"

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
    "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18,
}

VERSE_NUM_RE = re.compile(r"^(\d+(?:[-–]\d+)?)\.\s*(.*)$", re.S)
COMMENTARY_RE = re.compile(r"^\*{0,2}COMMENTARY:?\*{0,2}\s*(.*)$", re.S | re.I)


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
      - one or more consecutive italic-only <p> = Sanskrit lines
      - the next non-italic <p> starting "N. " or "N-M. " = translation
      - an optional following <p> starting "COMMENTARY:" = commentary
    """
    chapters = {}
    current_chapter = None
    current_title = None
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
                chapters[current_chapter] = {
                    "chapter": current_chapter,
                    "title": None,
                    "verses": [],
                }
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
            if m_comment and chapters[current_chapter]["verses"]:
                chapters[current_chapter]["verses"][-1]["commentary"] = m_comment.group(1).strip()
                continue

            m_verse = VERSE_NUM_RE.match(text)
            if m_verse:
                chapters[current_chapter]["verses"].append({
                    "number": m_verse.group(1),
                    "sanskrit": pending_sanskrit,
                    "translation": m_verse.group(2).strip(),
                })
                pending_sanskrit = []
                continue

            if is_italic_only(tag):
                pending_sanskrit.append(text)
                continue

            # anything else (chapter summaries, speaker tags, closing verses
            # of each discourse) is intentionally skipped — this scraper
            # only keeps numbered verses + their commentary.

    return chapters


def main():
    print(f"Fetching {SOURCE_URL} ...")
    soup = fetch_soup()
    print("Parsing ...")
    chapters = parse(soup)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_verses = 0
    for n in range(1, 19):
        ch = chapters.get(n)
        if not ch or not ch["verses"]:
            print(f"  ! chapter {n}: nothing parsed — check the source page structure "
                  f"or adjust the selectors in parse()", file=sys.stderr)
            continue
        out_path = OUT_DIR / f"chapter-{n:02d}.json"
        out_path.write_text(json.dumps(ch, ensure_ascii=False, indent=2), encoding="utf-8")
        total_verses += len(ch["verses"])
        print(f"  chapter {n:2d}: {ch['title']!r} — {len(ch['verses'])} verses -> {out_path.name}")

    print(f"\nDone. {total_verses} verses written to {OUT_DIR}/")
    if total_verses < 650:
        print("Note: the traditional count is 700 verses — if you're well under that, "
              "the parser likely missed some verses due to page-formatting quirks. "
              "Re-check parse() against the actual page HTML.", file=sys.stderr)


if __name__ == "__main__":
    main()
