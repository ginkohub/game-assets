#!/usr/bin/env python3
"""Scrape flag data from Wikipedia and save as data.json"""
import json, re, unicodedata
import requests
from bs4 import BeautifulSoup

URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "GameAssetsBot/1.0 (educational project)"}
PARAMS = {
    "action": "parse",
    "page": "List_of_national_flags_of_sovereign_states",
    "prop": "text",
    "format": "json",
    "origin": "*",
}

SKIP_CELL = {"—N/a", "Pavilion", "Flag of the Treinta y Tres", "Wiphala", "Rojinegra", "Artigas flag", "Artigas"}


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


def scrape():
    resp = requests.get(URL, params=PARAMS, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(resp.json()["parse"]["text"]["*"], "html.parser")
    results, seen = [], set()

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
        name = clean_name(raw)
        if not name:
            continue
        key = strip_diacritics(re.sub(r'\s*\(.*?\)\s*', '', name).strip()).lower()
        if key in seen:
            continue
        seen.add(key)

        src = img.get("src", "")
        if src.startswith("//"):
            src = "https:" + src
        elif not src.startswith("http"):
            src = "https:" + src
        src = re.sub(r'/thumb/', '/', src)
        src = re.sub(r'/\d+px-[^/]+$', '', src)

        results.append({"img": src, "jawaban": strip_diacritics(name)})

    results.sort(key=lambda x: x["jawaban"].lower())
    return results


if __name__ == "__main__":
    data = scrape()
    with open("data.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data)} entries to data.json")
