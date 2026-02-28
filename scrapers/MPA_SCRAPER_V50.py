#!/usr/bin/env python3
"""
MPA_SCRAPER_V30

Philosophy:
- MPADetail pages (boys + girls) are the ONLY source of truth for games & standings.
- No schedule scraping, no active-program lists.

Output:
- data/games_raw_v30.csv (ONE row per game, with EVERY detail from MPADetail,
  ready to join scores by GameID)
"""

import re
import time
from datetime import datetime, date
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Project root = parent of scrapers
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# ========== CONFIG ==========
MPA_DETAIL_URL = "https://www.mpa.cc/Custom/MPA/MPADetail.aspx"
TOURNAMENTS = {"Boys": 100, "Girls": 101}

# New v30-friendly raw output location
GAMES_OUTPUT = DATA_DIR / "games_raw_v30.csv"

SCRAPED_AT = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ========== LIGHT NAME CLEANING ==========
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
    """Canonical display name."""
    if not name:
        return None
    raw = normalize_school_pattern(str(name))
    return NAME_FIXES.get(raw, raw)


# ========== DATE HELPERS ==========
def parse_mpa_date(raw: str) -> str:
    """Convert mm/dd/yyyy -> yyyy-mm-dd."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(raw).strip())
    if not m:
        return raw
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return raw


# NOTE: parse_mpa_date already reads the 4-digit year directly from the
# MPADetail page, so no season-year inference is needed here.
# The dynamic year logic only lives in MPA_SCORES_SCRAPER where dates
# come in as MON MM/DD without a year.


# ========== SCRAPER ==========
def scrape_mpa_detail(gender: str, tournament_id: int):
    """
    Returns:
    - game_rows: list of dicts with ALL per-game details from MPADetail (one row per team per game),
      including the team header block (Results, GamesPlayed, GamesScheduled, PI, TI).
    """
    url = f"{MPA_DETAIL_URL}?TournamentID={tournament_id}"
    print(f"\n{'='*60}")
    print(f"Scraping {gender} basketball: {url}")
    print(f"{'='*60}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)  # let JS render
            html = page.content()
        except Exception as e:
            print(f"ERROR fetching {url}: {e}")
            browser.close()
            return []

        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    game_rows = []

    current_class    = ""
    current_region   = ""
    current_division = ""

    for node in soup.find_all(["h2", "h3"]):
        if node.name == "h2":
            text = normalize_space(node.get_text())
            m = re.match(r"DIVISION\s+(NORTH|SOUTH)-([A-DS])", text, re.IGNORECASE)
            if m:
                current_region   = m.group(1).title()
                current_class    = m.group(2).upper()
                current_division = f"{current_region}-{current_class}"
            continue

        # h3 = team block
        text = normalize_space(node.get_text())
        m = re.match(r"#(\d+)\s*-\s*(.+)", text)
        if not m:
            continue

        rank       = m.group(1)
        team_raw   = m.group(2).strip()
        current_team = clean_name(team_raw)

        sibling      = node.find_next_sibling()
        header_table = None
        game_table   = None

        while sibling:
            if sibling.name == "h3":
                break
            if sibling.name == "table":
                classes     = sibling.get("class", [])
                header_text = normalize_space(sibling.get_text())
                if (
                    "Results"    in header_text
                    and "Prelimnary" in header_text
                    and "Tournament" in header_text
                ):
                    header_table = sibling
                elif "teamgame" in classes:
                    game_table = sibling
            sibling = sibling.find_next_sibling()

        record_text      = ""
        games_played     = ""
        games_scheduled  = ""
        pi               = None
        ti               = None

        if header_table:
            rows = header_table.find_all("tr")
            if len(rows) >= 2:
                headers = [normalize_space(th.get_text()) for th in rows[0].find_all("th")]
                values  = [normalize_space(td.get_text()) for td in rows[1].find_all("td")]
                data    = dict(zip(headers, values))

                record_text      = data.get("Results", "")
                games_played     = data.get("Games Played", "")
                games_scheduled  = data.get("Games Scheduled", "")
                pi_raw           = data.get("Prelimnary", "")
                ti_raw           = data.get("Tournament", "")

                try:
                    pi = float(pi_raw) if pi_raw else None
                except Exception:
                    pi = None
                try:
                    ti = float(ti_raw) if ti_raw else None
                except Exception:
                    ti = None

        if game_table:
            tbody = game_table.find("tbody") or game_table
            for tr in tbody.find_all("tr"):
                if tr.find("th"):
                    continue
                cells = [normalize_space(td.get_text()) for td in tr.find_all("td")]
                if len(cells) < 10:
                    continue

                game_id   = cells[0]
                opponent  = clean_name(cells[1])
                opp_div   = cells[2]
                date_raw  = cells[3]
                game_num  = cells[4]
                win_flag  = cells[5]
                loss_flag = cells[6]
                tie_flag  = cells[7]
                win_points = cells[8]
                opp_pi    = cells[9]

                if   win_flag  == "X": result = "win"
                elif loss_flag == "X": result = "loss"
                elif tie_flag  == "X": result = "tie"
                else:                  result = "normal"

                date_val = parse_mpa_date(date_raw)

                try:
                    win_points_val = float(win_points) if win_points else None
                except Exception:
                    win_points_val = None
                try:
                    opp_pi_val = float(opp_pi) if opp_pi else None
                except Exception:
                    opp_pi_val = None

                game_rows.append({
                    "Date":                 date_val,
                    "Gender":               gender,
                    "GameID":               int(game_id),
                    "Team1":                current_team,
                    "Team2":                opponent,
                    "Result":               result,
                    "WinFlag":              win_flag,
                    "LossFlag":             loss_flag,
                    "TieFlag":              tie_flag,
                    "WinPoints":            win_points_val,
                    "OppPreliminaryIndex":  opp_pi_val,
                    "GameNum":              game_num,
                    "OppDiv":               opp_div,
                    "SchoolClass":          current_class,
                    "SchoolRegion":         current_region,
                    "SchoolDivision":       current_division,
                    "Rank":                 rank,
                    "RecordText":           record_text,
                    "GamesPlayed":          games_played,
                    "GamesScheduled":       games_scheduled,
                    "PI":                   pi,
                    "TI":                   ti,
                })

    print(f"  Extracted {len(game_rows)} team-game rows")
    return game_rows


def build_games_csv(all_games):
    """
    Collapse team-game rows into ONE row per GameID.
    Output contains EVERY MPADetail field we scraped,
    plus empty home/away + scores to be filled by the score scraper.
    """
    ensure_data_dir()

    df = pd.DataFrame(all_games)

    df["result_rank"] = df["Result"].map(
        {"win": 0, "tie": 1, "loss": 2, "normal": 3}
    ).fillna(3)
    df_played = (
        df.sort_values(["GameID", "result_rank"])
        .drop_duplicates(subset=["GameID"], keep="first")
        .copy()
    )

    # Drop unscored phantom games (no win/loss/tie flag set on MPA site)
    before = len(df_played)
    df_played = df_played[df_played["Result"] != "normal"].copy()
    after = len(df_played)
    if before != after:
        print(f"  ⚠ Dropped {before - after} unscored 'normal' games from output")


    games = []
    for _, r in df_played.iterrows():
        result = r["Result"]

        if   result == "win":  winner, loser = r["Team1"], r["Team2"]
        elif result == "loss": winner, loser = r["Team2"], r["Team1"]
        else:                  winner = loser = None

        games.append({
            "Date":                 r["Date"],
            "Gender":               r["Gender"],
            "GameID":               int(r["GameID"]),
            "Team1":                r["Team1"],
            "Team2":                r["Team2"],
            "SchoolClass":          r["SchoolClass"],
            "SchoolRegion":         r["SchoolRegion"],
            "SchoolDivision":       r["SchoolDivision"],
            "OppDiv":               r["OppDiv"],
            "GameNum":              r["GameNum"],
            "Rank":                 r["Rank"],
            "RecordText":           r["RecordText"],
            "GamesPlayed":          r["GamesPlayed"],
            "GamesScheduled":       r["GamesScheduled"],
            "PI":                   r["PI"],
            "TI":                   r["TI"],
            "Result":               result,
            "Winner":               winner,
            "Loser":                loser,
            "WinPoints":            r["WinPoints"],
            "OppPreliminaryIndex":  r["OppPreliminaryIndex"],
            "WinFlag":              r["WinFlag"],
            "LossFlag":             r["LossFlag"],
            "TieFlag":              r["TieFlag"],
            "HomeTeam":             "",
            "AwayTeam":             "",
            "HomeScore":            "",
            "AwayScore":            "",
            "ScrapedAt":            SCRAPED_AT,
        })

    df_games = pd.DataFrame(games)
    df_games.to_csv(GAMES_OUTPUT, index=False)
    print(f"✓ Wrote {len(df_games)} games to {GAMES_OUTPUT}")


def main():
    print("\n" + "=" * 60)
    print("MPA SCRAPER V30 - Fresh Start")
    print("=" * 60)

    all_games = []
    for gender, tid in TOURNAMENTS.items():
        games = scrape_mpa_detail(gender, tid)
        all_games.extend(games)

    build_games_csv(all_games)

    print("\n" + "=" * 60)
    print("V30 SCRAPE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
