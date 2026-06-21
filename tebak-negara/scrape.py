#!/usr/bin/env python3
"""Scrape flag data from Wikipedia, download PNGs, enrich with hints, save locally."""
import argparse, json, os, re, time, unicodedata, urllib.parse
import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(HERE, "images")

API_URL = "https://en.wikipedia.org/w/api.php"
WIKIDATA_URL = "https://query.wikidata.org/sparql"
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
    "Historical State flag of Lithuania": "Lithuania",
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
    ascii_chars = []
    for c in nfkd:
        if ord(c) < 128:
            ascii_chars.append(c)
        elif unicodedata.combining(c):
            continue
        elif c == '\u02bb':
            ascii_chars.append("'")
        else:
            ascii_chars.append(c)
    return ''.join(ascii_chars)


def slugify(name):
    s = name.lower().replace("'", "").replace("&", "and")
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s


def scrape_flags():
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
        name = clean_name(raw)
        name = NAME_OVERRIDE.get(raw, NAME_OVERRIDE.get(name, name))
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


def fetch_hints(country_names):
    """Fetch capital + region for each country via Wikipedia pageprops → Wikidata."""
    # Step 1: Get Wikidata Q IDs from Wikipedia page titles
    qid_map = {}  # country_name -> Q ID

    # Explicit Wikipedia title overrides for names that redirect to wrong pages
    TITLE_OVERRIDE = {
        "Georgia": "Georgia (country)",
        "Micronesia": "Federated States of Micronesia",
        "Sao Tome and Principe": "São Tomé and Príncipe",
        "Ireland": "Republic of Ireland",
    }

    for i in range(0, len(country_names), 50):
        batch = country_names[i:i+50]
        titles = [TITLE_OVERRIDE.get(n, n) for n in batch]
        params = {
            "action": "query",
            "prop": "pageprops",
            "titles": "|".join(titles),
            "format": "json",
            "origin": "*",
            "redirects": 1,
        }
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        for page in resp.json()["query"]["pages"].values():
            title = page.get("title", "")
            qid = page.get("pageprops", {}).get("wikibase_item", "")
            if title and qid:
                qid_map[title] = qid
        time.sleep(0.5)

    if not qid_map:
        return {}

    # Step 2: Batch query Wikidata for capital + continent
    qids = list(qid_map.values())
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""
    SELECT ?country ?capitalLabel ?continentLabel WHERE {{
      VALUES ?country {{ {values} }}
      OPTIONAL {{ ?country wdt:P36 ?capital. }}
      OPTIONAL {{ ?country wdt:P30 ?continent. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    resp = requests.get(WIKIDATA_URL, params={"query": query, "format": "json"},
                        headers=HEADERS, timeout=60)
    wd_data = resp.json()

    # Build reverse map: Q ID -> (continent, capital)
    wd_hints = {}
    for item in wd_data["results"]["bindings"]:
        qid = item["country"]["value"].split("/")[-1]
        capital = item.get("capitalLabel", {}).get("value", "")
        continent = item.get("continentLabel", {}).get("value", "")
        wd_hints[qid] = (continent, capital)

    # Step 3: Map back to country names
    # Build reverse map: slug(title) -> original country name
    def normalize(s):
        return re.sub(r'[^a-z0-9]+', '', s.lower())
    def normalize_loose(s):
        """Remove articles and normalize."""
        s = s.lower()
        for prefix in ["the ", "the country "]:
            if s.startswith(prefix):
                s = s[len(prefix):]
        return re.sub(r'[^a-z0-9]+', '', s)
    title_to_name = {}
    for name in country_names:
        for norm_fn in (normalize, normalize_loose):
            title_to_name[norm_fn(name)] = name
    # Also map override titles to original names
    for orig, override in TITLE_OVERRIDE.items():
        for norm_fn in (normalize, normalize_loose):
            title_to_name[norm_fn(override)] = orig

    result = {}
    for title, qid in qid_map.items():
        if qid in wd_hints:
            continent, capital = wd_hints[qid]
            # Find the original country name by several matching strategies
            soft_key = normalize_loose(title)
            hard_key = normalize(title)
            name = (
                title_to_name.get(hard_key)
                or title_to_name.get(soft_key)
                or next((n for n in country_names if normalize_loose(n) == soft_key), None)
                or next((n for n in country_names if normalize(n) == hard_key), None)
                or title
            )
            result[name] = {"wilayah": strip_diacritics(continent) if continent else "", "ibukota": strip_diacritics(capital) if capital else ""}
    return result


def download(entries):
    """Download PNGs and save locally with rate-limit delay."""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    results, seen_keys = [], set()
    total = len(entries)

    for i, (url, jawaban) in enumerate(entries, 1):
        key = jawaban.lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)

        fname = slugify(jawaban) + ".png"
        local_path = os.path.join(IMAGES_DIR, fname)
        rel_path = os.path.join("images", fname)

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            results.append({"bendera": rel_path, "negara": jawaban})
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
                results.append({"bendera": rel_path, "negara": jawaban})
                time.sleep(0.3)
                break
            except Exception as e:
                if attempt < 4:
                    wait = (attempt + 1) * 3
                    print(f"retry {wait}s)...", end=" ", flush=True)
                    time.sleep(wait)
                else:
                    print(f"FAILED: {e}")
                    results.append({"bendera": url, "negara": jawaban})

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape flag data from Wikipedia")
    parser.add_argument("-x", "--exclude", nargs="+", default=[],
                        help="Country names to exclude (case-insensitive)")
    args = parser.parse_args()
    exclude = set(e.lower() for e in args.exclude)

    print("Scraping Wikipedia...")
    entries = scrape_flags()
    print(f"Found {len(entries)} countries")

    print("Downloading thumbnails...")
    data = download(entries)

    # Filter excluded
    if exclude:
        before = len(data)
        data = [d for d in data if d["negara"].lower() not in exclude]
        print(f"Excluded {before - len(data)} countries ({', '.join(args.exclude)})")

    print("Fetching hints from Wikidata...")
    negara_list = [d["negara"] for d in data if d["bendera"].startswith("images/")]
    hints = fetch_hints(negara_list)
    for d in data:
        hint = hints.get(d["negara"])
        if hint:
            d["wilayah"] = hint["wilayah"]
            d["ibukota"] = hint["ibukota"]

    with open(os.path.join(HERE, "data.json"), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    local = sum(1 for d in data if d["bendera"].startswith("images/"))
    remote = len(data) - local
    hinted = sum(1 for d in data if d.get("wilayah") or d.get("ibukota"))
    print(f"Done: {local} local PNGs, {remote} fallback URLs, {hinted} enriched")
