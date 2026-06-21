#!/usr/bin/env python3
"""Scrape flag data from Wikipedia, download PNGs, save locally."""
import json, os, re, time, unicodedata
import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(HERE, "images")

API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "GameAssetsBot/1.0 (educational project)"}
PARAMS = {
    "action": "parse",
    "page": "List_of_national_flags_of_sovereign_states",
    "prop": "text",
    "format": "json",
    "origin": "*",
}
SKIP_CELL = {"—N/a", "Pavilion", "Flag of the Treinta y Tres", "Wiphala", "Rojinegra", "Artigas flag", "Artigas"}
NAME_OVERRIDE = {
    "National Pavilion": "Uruguay",
    "State flag and Civil flag of Poland": "Poland",
    "State flag of Lithuania": "Lithuania",
    "Paraguay(obverse)": "Paraguay",
}


def clean_name(raw):
    name = raw.strip()
    for p in ["Civil flag of ", "Civil Flag of ", "Civil ensign of ",
              "State flag of ", "State Flag of ", "National flag of ", "National Flag of "]:
        if name.startswith(p):
            name = name[len(p):]
            break
    name = re.sub(r'\[.*?\]', '', name).strip()
    name = re.sub(r'^Historical\s+', '', name)
    if name.startswith("the "):
        name = name[4:].strip().capitalize()
    return name


def strip_diacritics(s):
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def slugify(name):
    s = name.lower().replace("'", "").replace("&", "and")
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s


def scrape():
    """Parse Wikipedia table and return list of (png_url, country_name)."""
    resp = requests.get(API_URL, params=PARAMS, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(resp.json()["parse"]["text"]["*"], "html.parser")
    entries, seen = [], set()

    for row in soup.select_one("table.wikitable").select("tr"):
        cells = row.select("td")
        if not cells:
            continue
        img = cells[0].select_one("img")
        if not img:
            continue
        raw = cells[0].get_text(strip=True)
        if not raw or raw in SKIP_CELL or re.match(r'^\d', raw):
            continue
        name = NAME_OVERRIDE.get(raw, clean_name(raw))
        if not name:
            continue
        jawaban = strip_diacritics(re.sub(r'\s*\(.*?\)\s*', '', name).strip())
        key = jawaban.lower()
        if key in seen:
            continue
        seen.add(key)

        src = img.get("src", "")
        if src.startswith("//"):
            src = "https:" + src

        entries.append((src, jawaban))

    entries.sort(key=lambda x: x[1].lower())
    return entries


def download(entries):
    """Download PNGs and save locally with rate-limit delay."""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    results = []
    total = len(entries)

    for i, (url, jawaban) in enumerate(entries, 1):
        fname = slugify(jawaban) + ".png"
        local_path = os.path.join(IMAGES_DIR, fname)
        rel_path = os.path.join("images", fname)

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            results.append({"img": rel_path, "jawaban": jawaban})
            continue

        print(f"  [{i}/{total}] {jawaban}...", end=" ", flush=True)
        for attempt in range(5):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                if resp.status_code == 429:
                    wait = (attempt + 1) * 5
                    print(f"429 (retry {wait}s)...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                print(f"ok ({len(resp.content)} bytes)")
                results.append({"img": rel_path, "jawaban": jawaban})
                time.sleep(0.3)
                break
            except Exception as e:
                if attempt < 4:
                    wait = (attempt + 1) * 3
                    print(f"retry {wait}s)...", end=" ", flush=True)
                    time.sleep(wait)
                else:
                    print(f"FAILED: {e}")
                    results.append({"img": url, "jawaban": jawaban})

    return results


if __name__ == "__main__":
    print("Scraping Wikipedia...")
    entries = scrape()
    print(f"Found {len(entries)} countries")

    print("Downloading thumbnails...")
    data = download(entries)

    with open(os.path.join(HERE, "data.json"), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    local = sum(1 for d in data if d["img"].startswith("images/"))
    remote = len(data) - local
    print(f"Done: {local} local PNGs, {remote} fallback URLs")
