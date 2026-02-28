#!/usr/bin/env python3
"""
MPA_SCORES_SCRAPER_V30

Goal:
- For each varsity game with a recorded score, capture:
  GameID, HomeTeam, AwayTeam, HomeScore, AwayScore, timestamp.

Output:
- data/games_scores_v30.csv
"""

import re
import time
import json
from datetime import datetime, date
from io import StringIO
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

# ---------- CONFIG ----------
MPA_DETAIL_URL = "https://www.mpa.cc/Custom/MPA/MPADetail.aspx"
SCHOOL_LIST_URL = "https://www.mpa.cc/SchoolPages/School.aspx"

# Boys Varsity = 2, Girls Varsity = 3 on School.aspx schedules tab
SGLID_BY_GENDER = {"Boys": 2, "Girls": 3}
TOURNAMENTS = {"Boys": 100, "Girls": 101}

# Project root (parent of scrapers)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

# Write scores file into data/ so join + nightly can see it
SCORES_OUTPUT = DATA_DIR / "games_scores_v30.csv"
SCORES_SCRAPED_AT = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

# JSON caches live in data/
ACTIVE_PROGRAMS_FILE = DATA_DIR / "active_basketball_programs.json"
NO_PROGRAMS_FILE     = DATA_DIR / "no_basketball_programs.json"

NON_HS_BLACKLIST = {"Cony Middle School"}

# ---------- LIGHT NAME CLEANING ----------
NAME_FIXES = {
    "Sumner (Charles M.) Learning Campus":    "Sumner Memorial",
    "Sumner Memorial":                         "Sumner Memorial",
    "Southern Aroostook Community School":     "Southern Aroostook",
    "Van Buren District Secondary School":     "Van Buren District",
    "Camden Hills Regional High School":       "Camden Hills Regional",
    "Camden Hills Regional":                   "Camden Hills Regional",
    "Houlton HS":                              "Houlton HS",
    "Houlton High School":                     "Houlton HS",
    "Hodgdon HS":                              "Hodgdon HS",
    "Islesboro Central School":                "Islesboro Central",
    "Cony HS":                                 "Cony HS",
    "Fort Fairfield HS":                       "Fort Fairfield HS",
    "Katahdin HS":                             "Katahdin HS",
    "Madawaska HS":                            "Madawaska HS",
    "Oxford Hills Comprehensive High School":  "Oxford Hills",
    "Oxford Hills Comprehensive":              "Oxford Hills",
    "Penquis Valley HS":                       "Penquis Valley HS",
    "Rangeley Lakes Regional":                 "Rangeley Lakes Regional",
    "Richmond HS":                             "Richmond HS",
    "Searsport HS":                            "Searsport HS",
    "Stearns Sr.":                             "Stearns Sr.",
    "Temple Academy":                          "Temple Academy",
    "Washburn District":                       "Washburn District",
    "Mt. Blue":                                "Mount Blue",
    "Mt. Abram":                               "Mount Abram",
    "Mt. Ararat":                              "Mount Ararat",
    # ── Dexter / PCHS co-op (all variants MPA may render) ──
    "Dexter Regional":                         "Dexter Regional",
    "Dexter Regional High School":             "Dexter Regional",
    "Dexter/PCHS":                             "Dexter Regional",
    "Dexter PCHS":                             "Dexter Regional",
    "DexterPCHS":                              "Dexter Regional",
    "Piscataquis Community Secondary School":  "Dexter Regional",
    "Piscataquis Community":                   "Dexter Regional",
    # ────────────────────────────────────────────────────────
    "Fort Kent Community":                     "Fort Kent Community",
    "Buckfield HS":                            "Buckfield HS",
    "Wiscasset HS":                            "Wiscasset HS",
    "Hall-Dale HS":                            "Hall-Dale HS",
    "Monmouth Academy":                        "Monmouth Academy",
    "North Yarmouth Academy":                  "North Yarmouth Academy",
    "Old Orchard Beach":                       "Old Orchard Beach",
    "Telstar Regional":                        "Telstar Regional",
    "Boothbay Region":                         "Boothbay Region",
    "Upper Kennebec Valley High School":       "Valley HS",
    "Pine Tree Academy":                       "Pine Tree Academy",
    "Forest Hills Consolidated":               "Forest Hills Consolidated",
    "Vinalhaven":                              "Vinalhaven",
}


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def normalize_school_pattern(name: str) -> str:
    s = str(name).strip()
    s = re.sub(r"\bMt\.?\s+", "Mount ", s)
    s = s.replace(" Highschool", " High School")
    s = s.replace(" High-school", " High School")
    s = s.replace(" H.S.", " HS")
    return normalize_space(s)


def clean_name(name: str) -> str | None:
    if not name:
        return None
    raw = normalize_school_pattern(str(name))
    return NAME_FIXES.get(raw, raw)


def norm_name(x: str) -> str:
    if x is None:
        return ""
    s = clean_name(x)
    s = normalize_space(str(s)).lower()
    s = s.replace("&", "and").replace(".", "")
    return s


def is_non_hs(name: str) -> bool:
    if not name:
        return False
    n = str(name).lower()
    if "middle" in n or "jr." in n or "junior" in n:
        return True
    if name in NON_HS_BLACKLIST:
        return True
    return False


# ---------- DATE HELPERS ----------
def parse_schedule_date(raw: str) -> str:
    raw = str(raw).strip()
    m = re.match(r"[A-Z]{3}\s+(\d{1,2})/(\d{1,2})", raw)
    if not m:
        return raw
    month = int(m.group(1))
    day   = int(m.group(2))
    # Season runs Nov–Mar; auto-detect year so this never needs manual updates
    current_year = date.today().year
    year = current_year - 1 if month >= 11 else current_year
    try:
        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return raw


def parse_mpa_detail_date(raw: str) -> str:
    raw = str(raw).strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if not m:
        return raw
    month = int(m.group(1))
    day   = int(m.group(2))
    year  = int(m.group(3))
    try:
        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return raw


# ---------- JSON cache helpers ----------
def load_json_id_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            if data and isinstance(data[0], dict) and "id" in data[0]:
                return {str(x["id"]) for x in data}
            return {str(x) for x in data}
    except Exception:
        return set()
    return set()


def save_json_id_list(path: Path, ids: set[str]) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sorted(list(ids)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"WARNING: could not save {path}: {e}")


# ---------- SCHOOL LIST ----------
def get_all_schools(page):
    schools = []
    try:
        print("Loading school list from School.aspx...")
        page.goto(SCHOOL_LIST_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector(".SchoolSearchResults", timeout=10000)
        soup = BeautifulSoup(page.content(), "html.parser")
        results = soup.select(".SchoolSearchResults a[href*='SchoolID=']")
        seen = set()
        for a in results:
            href = a.get("href", "")
            m = re.search(r"SchoolID=(\d+)", href)
            if not m:
                continue
            sid = m.group(1)
            if sid in seen:
                continue
            name_el = a.select_one(".SchoolListName")
            if not name_el:
                continue
            name = normalize_space(name_el.get_text())
            if is_non_hs(name):
                print(f"  Skipping non-HS: {name}")
                continue
            schools.append({"id": sid, "name": name})
            seen.add(sid)
        print(f"Found {len(schools)} high schools (after filtering)")
        return schools
    except Exception as e:
        print(f"Error getting school list: {e}")
        return schools


# ---------- MPADetail: get GameID per school ----------
def parse_mpa_detail_table(html: str, school_name: str, gender: str):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", {"class": "teamgame"})
    if not tables:
        return []
    table_html = str(tables[0])
    try:
        df_list = pd.read_html(StringIO(table_html))
    except ValueError:
        return []
    if not df_list:
        return []
    df = df_list[0]
    df.columns = [normalize_space(str(c)) for c in df.columns]

    games = []
    for _, row in df.iterrows():
        try:
            game_id  = row.get("Game ID")
            opponent = row.get("Opponent")
            date_raw = row.get("Date")
            if pd.isna(game_id) or pd.isna(opponent) or pd.isna(date_raw):
                continue
            games.append({
                "GameID":    int(game_id),
                "school":    clean_name(school_name),
                "gender":    gender,
                "opponent":  clean_name(normalize_space(opponent)),
                "date":      parse_mpa_detail_date(str(date_raw)),
            })
        except Exception:
            continue
    return games


def scrape_mpa_detail_for_school(page, school_id: str, school_name: str):
    all_games = []
    for gender, tid in TOURNAMENTS.items():
        url = f"{MPA_DETAIL_URL}?Status=0&SchoolID={school_id}&TournamentID={tid}"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("table.teamgame", timeout=5000)
            html  = page.content()
            games = parse_mpa_detail_table(html, school_name, gender)
            all_games.extend(games)
        except PlaywrightTimeout:
            continue
        except Exception as e:
            print(f"Error scraping MPADetail {url}: {e}")
            continue
    return all_games


# ---------- SCHEDULES: get scores per school ----------
def find_varsity_schedule_table(soup, gender: str):
    target_gender = gender.lower()
    for h2 in soup.find_all("h2"):
        text = normalize_space(h2.get_text()).lower()
        if "basketball" not in text:
            continue
        if target_gender not in text:
            continue
        if "varsity" not in text:
            continue
        wrapper = h2.find_next("div", class_="dsTableWrapper")
        if not wrapper:
            continue
        table = wrapper.find("table", class_="tableregularseason")
        if table:
            return table
    tables = soup.select("table.tableregularseason")
    for table in tables:
        caption_el = table.find_previous("h2")
        if not caption_el:
            continue
        heading = normalize_space(caption_el.get_text()).lower()
        if gender.lower() in heading and "varsity" in heading:
            return table
    return None


def scrape_schedule_for_school(page, school_id: str, school_name: str, gender: str):
    sglid = SGLID_BY_GENDER.get(gender)
    if not sglid:
        return []

    url = f"{SCHOOL_LIST_URL}?SchoolID={school_id}&tab=schedules&SGLID={sglid}"
    print(f"  Schedule: {school_name} {gender} -> {url}")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("table.tableregularseason", timeout=10000)
        soup = BeautifulSoup(page.content(), "html.parser")

        table = find_varsity_schedule_table(soup, gender)
        if table is None:
            print("   No varsity schedule table found")
            return []

        df_list = pd.read_html(StringIO(str(table)))
        if not df_list:
            print("   Empty schedule table")
            return []

        df = df_list[0]
        df.columns = [normalize_space(str(c)) for c in df.columns]

        cols      = list(df.columns)
        renamemap = {}
        if "Date" in cols:
            renamemap["Date"] = "date_raw"
        if "Type" in cols:
            renamemap["Type"] = "game_type"
        for cand in ["H/A", "H / A", "HA"]:
            if cand in cols:
                renamemap[cand] = "ha_flag"
                break
        for cand in ["Opponent", "Opp"]:
            if cand in cols:
                renamemap[cand] = "opponent_sched"
                break
        if "Result" in cols:
            renamemap["Result"] = "score_text"
        if "Score" in cols:
            renamemap["Score"] = "score_text"

        df = df.rename(columns=renamemap)

        if "game_type" in df.columns:
            df["game_type"] = df["game_type"].astype(str)
            df = df[df["game_type"].str.strip().str.lower() == "league"]

        if (
            "date_raw"       not in df.columns
            or "ha_flag"     not in df.columns
            or "opponent_sched" not in df.columns
        ):
            print("   Required columns not found, skipping schedule.")
            return []

        df["date"]          = df["date_raw"].apply(parse_schedule_date)
        df["gender"]        = gender
        df["opponent_sched"] = df["opponent_sched"].astype(str).apply(
            lambda x: clean_name(normalize_space(x))
        )
        df["ha_flag"] = df["ha_flag"].astype(str).str.strip().str.upper()

        def parse_score_parts(s: str):
            s = str(s).strip()
            m = re.search(r"(\d+)\s*-\s*(\d+)", s)
            if not m:
                return None, None
            return int(m.group(1)), int(m.group(2))

        def get_result(row):
            txt = str(row.get("score_text", "")).lower()
            if "win"  in txt: return "win"
            if "loss" in txt or "lost" in txt: return "loss"
            if "tie"  in txt: return "tie"
            return None

        def infer_school_and_opp_points(row):
            pts1, pts2 = parse_score_parts(row.get("score_text", ""))
            if pts1 is None:
                return None, None
            result = get_result(row)
            school_pts, opp_pts = pts1, pts2
            if result == "win"  and school_pts < opp_pts:
                school_pts, opp_pts = opp_pts, school_pts
            elif result == "loss" and school_pts > opp_pts:
                school_pts, opp_pts = opp_pts, school_pts
            return school_pts, opp_pts

        rows         = []
        school_clean = clean_name(school_name)

        for _, row in df.iterrows():
            sp, op = infer_school_and_opp_points(row)
            if sp is None or op is None:
                continue

            opp = row["opponent_sched"]
            ha  = row["ha_flag"]

            if ha == "H":
                home_team, away_team = school_clean, opp
                home_score, away_score = sp, op
            elif ha == "A":
                home_team, away_team = opp, school_clean
                home_score, away_score = op, sp
            else:
                home_team, away_team = school_clean, opp
                home_score, away_score = sp, op

            rows.append({
                "school":     school_clean,
                "gender":     gender,
                "opponent":   opp,
                "date":       row["date"],
                "ha":         ha,
                "HomeTeam":   clean_name(home_team),
                "AwayTeam":   clean_name(away_team),
                "HomeScore":  float(home_score),
                "AwayScore":  float(away_score),
            })

        print(f"   Parsed scores for {len(rows)} schedule rows")
        return rows

    except PlaywrightTimeout:
        print(f"   Timeout on schedule {url}")
        return []
    except Exception as e:
        print(f"   Error scraping schedule {url}: {e}")
        return []


# ---------- MERGE ----------
def merge_scores(mpa_games, sched_games):
    sched_index: dict[tuple[str, str, str, str], list[dict]] = {}
    for s in sched_games:
        key = (norm_name(s["school"]), s["gender"], s["date"], norm_name(s["opponent"]))
        sched_index.setdefault(key, []).append(s)

    score_rows = []
    for m in mpa_games:
        key = (norm_name(m["school"]), m["gender"], m["date"], norm_name(m["opponent"]))
        candidates = sched_index.get(key, [])
        if not candidates:
            continue
        s = candidates[0]
        score_rows.append({
            "GameID":         m["GameID"],
            "HomeTeam":       s["HomeTeam"],
            "AwayTeam":       s["AwayTeam"],
            "HomeScore":      s["HomeScore"],
            "AwayScore":      s["AwayScore"],
            "ScoresScrapedAt": SCORES_SCRAPED_AT,
        })

    return score_rows


# ---------- PROGRAM PROBE ----------
def school_has_any_basketball(page, sid: str, name: str) -> bool:
    for gender, tid in TOURNAMENTS.items():
        detail_url = f"{MPA_DETAIL_URL}?Status=0&SchoolID={sid}&TournamentID={tid}"
        try:
            page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
            soup = BeautifulSoup(page.content(), "html.parser")
            if soup.find("table", {"class": "teamgame"}):
                print(f"  ✓ {name} has {gender} basketball")
                return True
        except Exception:
            pass
    print(f"  ✗ {name} has NO varsity basketball")
    return False


# ---------- MAIN SCRAPE ----------
def scrape_scores(page, schools):
    all_score_rows = []

    print(f"Scraping scores for {len(schools)} schools...")
    for idx, s in enumerate(schools, start=1):
        sid  = s["id"]
        name = s["name"]
        print("-" * 70)
        print(f"[{idx}/{len(schools)}] {name} (SchoolID={sid})")

        mpa_games = scrape_mpa_detail_for_school(page, sid, name)
        if not mpa_games:
            print("  No MPADetail games; skipping scores merge.")
            continue

        sched_games = []
        for gender in ["Boys", "Girls"]:
            sched_games.extend(scrape_schedule_for_school(page, sid, name, gender))

        if not sched_games:
            print("  No schedule scores; skipping merge for this school.")
            continue

        merged = merge_scores(mpa_games, sched_games)
        print(f"  Score rows produced: {len(merged)}")
        all_score_rows.extend(merged)

    return all_score_rows


def main():
    print("\n" + "=" * 60)
    print("MPA_SCORES_SCRAPER_V30 - Scores only (MPADetail + Schedules)")
    print("=" * 60)

    ensure_data_dir()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            ),
        )
        page = context.new_page()

        schools = get_all_schools(page)
        if not schools:
            print("No schools found; aborting.")
            browser.close()
            return

        active_ids    = load_json_id_set(ACTIVE_PROGRAMS_FILE)
        no_program_ids = load_json_id_set(NO_PROGRAMS_FILE)

        to_classify = [
            s for s in schools
            if s["id"] not in active_ids and s["id"] not in no_program_ids
        ]

        if to_classify:
            print(f"Probing {len(to_classify)} schools for active basketball programs...")
            for s in to_classify:
                sid  = s["id"]
                name = s["name"]
                print(f" Probing {name} (SchoolID={sid})...")
                if school_has_any_basketball(page, sid, name):
                    active_ids.add(sid)
                else:
                    no_program_ids.add(sid)
                time.sleep(0.2)

            save_json_id_list(ACTIVE_PROGRAMS_FILE, active_ids)
            save_json_id_list(NO_PROGRAMS_FILE, no_program_ids)

        if active_ids:
            schools = [s for s in schools if s["id"] in active_ids]
            print(
                f"Using {len(schools)} schools with active basketball programs "
                f"(skipping non-program schools)."
            )

        all_score_rows = scrape_scores(page, schools)
        browser.close()

    ensure_data_dir()
    df = pd.DataFrame(all_score_rows).drop_duplicates(subset=["GameID"], keep="last")
    df.to_csv(SCORES_OUTPUT, index=False)
    print(f"✓ Wrote {len(df)} games with scores to {SCORES_OUTPUT}")


if __name__ == "__main__":
    main()
