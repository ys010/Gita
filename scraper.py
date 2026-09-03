#!/usr/bin/env python3
"""Scrape the Bhagavad Gita (Sanskrit + translation + commentary) into
data/chapter-NN.json, one file per chapter, one record per verse.

Source: the vedicscriptures/bhagavad-gita dataset, published live on
raw.githubusercontent.com. Each chapter and each verse is served as its own
JSON resource there (chapter/bhagavadgita_chapter_<n>.json and
slok/bhagavadgita_chapter_<n>_slok_<v>.json), so this fetches and parses
every chapter and verse page individually, the same way it would page
through per-verse HTML on any other Gita site. BeautifulSoup is used in
clean_text() to strip stray markup some commentary fields carry.

For each verse it walks a fixed chain of commentators (Prabhupada first,
then Sivananda, etc.) and keeps the first one that has both a translation
and a commentary, since not every commentator covers every verse.
"""
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

CHAPTER_URL = "https://raw.githubusercontent.com/vedicscriptures/bhagavad-gita/master/chapter/bhagavadgita_chapter_{ch}.json"
SLOK_URL = "https://raw.githubusercontent.com/vedicscriptures/bhagavad-gita/master/slok/bhagavadgita_chapter_{ch}_slok_{v}.json"

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# (json key, display name) in priority order: first commentator with both
# a translation and a commentary for a given verse wins.
COMMENTATOR_CHAIN = [
    ("prabhu", "A.C. Bhaktivedanta Swami Prabhupada"),
    ("siva", "Swami Sivananda"),
    ("tej", "Swami Tejomayananda"),
    ("chinmay", "Swami Chinmayananda"),
    ("adi", "Swami Adidevananda"),
    ("purohit", "Shri Purohit Swami"),
]


def clean_text(text):
    if not text:
        return ""
    text = BeautifulSoup(text, "html.parser").get_text()
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_json(url, retries=4):
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_err}")


def pick_translation_and_commentary(verse_json):
    for key, display_name in COMMENTATOR_CHAIN:
        block = verse_json.get(key)
        if not block:
            continue
        translation = block.get("et") or block.get("ht")
        commentary = block.get("ec")
        if translation and commentary and commentary.strip() != translation.strip():
            return {
                "author": block.get("author", display_name),
                "translation": clean_text(translation),
                "commentary": clean_text(commentary),
            }
        if translation and not commentary:
            # Keep looking for a commentator who *also* has a commentary,
            # but remember this as a fallback translation-only match.
            continue
    # Second pass: accept translation-only if nothing better was found.
    for key, display_name in COMMENTATOR_CHAIN:
        block = verse_json.get(key)
        if not block:
            continue
        translation = block.get("et") or block.get("ht")
        if translation:
            return {
                "author": block.get("author", display_name),
                "translation": clean_text(translation),
                "commentary": "",
            }
    return {"author": "", "translation": "", "commentary": ""}


def scrape_chapter(ch):
    meta = fetch_json(CHAPTER_URL.format(ch=ch))
    verse_count = meta["verses_count"]
    verses = []
    for v in range(1, verse_count + 1):
        vd = fetch_json(SLOK_URL.format(ch=ch, v=v))
        tc = pick_translation_and_commentary(vd)
        verses.append(
            {
                "chapter": ch,
                "verse": v,
                "speaker": vd.get("speaker", "") or "",
                "sanskrit": clean_text(vd.get("slok")),
                "transliteration": clean_text(vd.get("transliteration")),
                "translation": tc["translation"],
                "commentary": tc["commentary"],
                "commentary_author": tc["author"],
            }
        )
        time.sleep(0.03)
    return {
        "chapter": ch,
        "title_sanskrit": meta.get("name", ""),
        "title_transliteration": meta.get("transliteration", ""),
        "title_translation": meta.get("translation", ""),
        "summary": (meta.get("summary") or {}).get("en", ""),
        "verse_count": verse_count,
        "verses": verses,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total_verses = 0
    for ch in range(1, 19):
        print(f"Scraping chapter {ch}...")
        data = scrape_chapter(ch)
        out_path = os.path.join(OUT_DIR, f"chapter-{ch:02d}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  wrote {out_path} ({len(data['verses'])} verses)")
        total_verses += len(data["verses"])
    print(f"Done. {total_verses} verses across 18 chapters.")


if __name__ == "__main__":
    main()
