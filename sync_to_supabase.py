import numpy as np
import pandas as pd
from supabase import create_client

SUPABASE_URL = "https://lofxbafahfogptdkjhhv.supabase.co"
import os
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PATHS = {
    "schooldirectory": "data/schooldirectory.csv",
    "games_raw": "data/games_raw_v30.csv",
    "games_scores": "data/games_scores_v30.csv",
    "truth": "data/truth.csv",
    "tournament_bracket": "data/tournament/2026/tournament_2026_bracket.csv",
    "tournament_results": "data/tournament/2026/tournament_2026_results.csv",
    "tournament_boys_full": "data/tournament/2026/tournament_2026_boys_full.csv",
    "tournament_boys_preds": "data/tournament/2026/tournament_2026_boys_with_predictions.csv",
    "pick5_participants": "data/pick5/pick5_participants.csv",
    "pick_5_rosters": "data/pick_5_rosters.csv",
    "team_of_week_votes": "data/totw/team_of_week_votes.csv",
    "milestone_claims": "data/milestone_claims.csv",
    "milestone_votes": "data/milestone_votes.csv",
}


def clean(df):
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    return df


def sanitize_records(records):
    import math
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                rec[k] = None
    return records


def upsert_batched(table_name, records, batch_size=500, on_conflict="id"):
    records = sanitize_records(records)
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        supabase.table(table_name).upsert(batch, on_conflict=on_conflict).execute()
    print(f"  ✓ {table_name}: {total} rows")


def sync_school_directory():
    df = clean(pd.read_csv(PATHS["schooldirectory"]))
    records = df.rename(columns={
        "SCHOOL NAME": "school_name", "ADDRESS": "address",
        "CITY": "city", "STATE": "state", "ZIP": "zip"
    }).to_dict(orient="records")
    upsert_batched("school_directory", records, on_conflict="school_name")


def sync_games_raw():
    df = clean(pd.read_csv(PATHS["games_raw"]))
    records = df.rename(columns={
        "Date": "date", "Gender": "gender", "GameID": "game_id",
        "Team1": "team1", "Team2": "team2", "SchoolClass": "school_class",
        "SchoolRegion": "school_region", "SchoolDivision": "school_division",
        "OppDiv": "opp_div", "GameNum": "game_num", "Rank": "rank",
        "RecordText": "record_text", "GamesPlayed": "games_played",
        "GamesScheduled": "games_scheduled", "PI": "pi", "TI": "ti",
        "Result": "result", "Winner": "winner", "Loser": "loser",
        "WinPoints": "win_points", "OppPreliminaryIndex": "opp_preliminary_index",
        "WinFlag": "win_flag", "LossFlag": "loss_flag", "TieFlag": "tie_flag",
        "HomeTeam": "home_team", "AwayTeam": "away_team",
        "HomeScore": "home_score", "AwayScore": "away_score",
        "ScrapedAt": "scraped_at"
    }).to_dict(orient="records")
    upsert_batched("games_raw", records, on_conflict="game_id")


def sync_games_scores():
    df = clean(pd.read_csv(PATHS["games_scores"]))
    records = df.rename(columns={
        "GameID": "game_id", "HomeTeam": "home_team", "AwayTeam": "away_team",
        "HomeScore": "home_score", "AwayScore": "away_score",
        "ScoresScrapedAt": "scores_scraped_at"
    }).to_dict(orient="records")
    upsert_batched("games_scores", records, on_conflict="game_id")


def sync_truth():
    df = clean(pd.read_csv(PATHS["truth"]))
    records = df.rename(columns={
        "Date": "date", "Gender": "gender", "GameID": "game_id",
        "Team1": "team1", "Team2": "team2", "SchoolClass": "school_class",
        "SchoolRegion": "school_region", "SchoolDivision": "school_division",
        "OppDiv": "opp_div", "GameNum": "game_num", "Rank": "rank",
        "RecordText": "record_text", "GamesPlayed": "games_played",
        "GamesScheduled": "games_scheduled", "PI": "pi", "TI": "ti",
        "Result": "result", "Winner": "winner", "Loser": "loser",
        "WinPoints": "win_points", "OppPreliminaryIndex": "opp_preliminary_index",
        "WinFlag": "win_flag", "LossFlag": "loss_flag", "TieFlag": "tie_flag",
        "HomeTeam": "home_team", "AwayTeam": "away_team",
        "HomeScore": "home_score", "AwayScore": "away_score",
        "ScrapedAt": "scraped_at"
    }).to_dict(orient="records")
    upsert_batched("truth", records, on_conflict="game_id")


def sync_tournament_bracket():
    df = clean(pd.read_csv(PATHS["tournament_bracket"]))
    df = df.drop(columns=["Score1", "Score2"], errors="ignore")
    records = df.rename(columns={
        "Season": "season", "Gender": "gender", "Class": "class",
        "Region": "region", "Round": "round", "GameID": "game_id",
        "Seed1": "seed1", "Team1": "team1", "Seed2": "seed2", "Team2": "team2",
        "TeamKey1": "team_key1", "TeamKey2": "team_key2",
        "PIR1": "pir1", "PIR2": "pir2",
        "PredWinProb1": "pred_win_prob1", "PredWinProb2": "pred_win_prob2",
        "PredScore1": "pred_score1", "PredScore2": "pred_score2",
        "PredMargin": "pred_margin", "PredTotal": "pred_total",
        "PredWinner": "pred_winner"
    }).to_dict(orient="records")
    upsert_batched("tournament_bracket", records, on_conflict="game_id")


def sync_tournament_results():
    df = clean(pd.read_csv(PATHS["tournament_results"]))
    records = df.rename(columns={
        "Season": "season", "Gender": "gender", "Class": "class",
        "Region": "region", "Round": "round", "GameID": "game_id",
        "Seed1": "seed1", "Team1": "team1", "Score1": "score1",
        "Seed2": "seed2", "Team2": "team2", "Score2": "score2",
        "Winner": "winner", "OT": "ot", "PIR1": "pir1", "PIR2": "pir2",
        "PredWinner": "pred_winner", "PredWinProb1": "pred_win_prob1",
        "PredScore1": "pred_score1", "PredScore2": "pred_score2",
        "PredMargin": "pred_margin"
    }).to_dict(orient="records")
    upsert_batched("tournament_results", records, on_conflict="game_id")


def sync_tournament_boys_full():
    df = clean(pd.read_csv(PATHS["tournament_boys_full"]))
    records = df.rename(columns={
        "Class": "class", "Region": "region", "Round": "round",
        "GameID": "game_id", "Seed1": "seed1", "Team1": "team1",
        "Score1": "score1", "Seed2": "seed2", "Team2": "team2", "Score2": "score2"
    }).to_dict(orient="records")
    upsert_batched("tournament_boys_full", records, on_conflict="game_id")


def sync_tournament_boys_with_predictions():
    df = clean(pd.read_csv(PATHS["tournament_boys_preds"]))
    records = df.rename(columns={
        "Class": "class", "Region": "region", "Round": "round",
        "GameID": "game_id", "Seed1": "seed1", "Team1": "team1",
        "Score1": "score1", "Seed2": "seed2", "Team2": "team2", "Score2": "score2"
    }).to_dict(orient="records")
    upsert_batched("tournament_boys_with_predictions", records, on_conflict="game_id")


def sync_pick5_participants():
    df = clean(pd.read_csv(PATHS["pick5_participants"]))
    records = df.rename(columns={
        "Name": "name", "PIN_hash": "pin_hash"
    }).to_dict(orient="records")
    upsert_batched("pick5_participants", records, on_conflict="name")


def sync_pick_5_rosters():
    df = clean(pd.read_csv(PATHS["pick_5_rosters"]))
    records = df.rename(columns={
        "Manager": "manager", "Week": "week", "Gender": "gender",
        "ClassA_Pick": "class_a_pick", "ClassA_Pts": "class_a_pts",
        "ClassB_Pick": "class_b_pick", "ClassB_Pts": "class_b_pts",
        "ClassC_Pick": "class_c_pick", "ClassC_Pts": "class_c_pts",
        "ClassD_Pick": "class_d_pick", "ClassD_Pts": "class_d_pts",
        "ClassS_Pick": "class_s_pick", "ClassS_Pts": "class_s_pts",
        "MaxPossible": "max_possible", "CreatedAt": "created_at"
    }).to_dict(orient="records")
    upsert_batched("pick_5_rosters", records, on_conflict="manager,week,gender")


def sync_team_of_week_votes():
    df = clean(pd.read_csv(PATHS["team_of_week_votes"]))
    records = df.rename(columns={
        "Timestamp": "timestamp", "WeekID": "week_id",
        "Segment": "segment", "Pick": "pick", "TeamKey": "team_key"
    }).to_dict(orient="records")
    supabase.table("team_of_week_votes").delete().neq("id", 0).execute()
    upsert_batched("team_of_week_votes", records)


def sync_milestone_claims():
    df = clean(pd.read_csv(PATHS["milestone_claims"]))
    records = df.to_dict(orient="records")
    upsert_batched("milestone_claims", records, on_conflict="claim_id")


def sync_milestone_votes():
    df = clean(pd.read_csv(PATHS["milestone_votes"]))
    records = df.to_dict(orient="records")
    supabase.table("milestone_votes").delete().neq("id", 0).execute()
    upsert_batched("milestone_votes", records)


if __name__ == "__main__":
    print("Starting sync to Supabase...")
    print()
    sync_school_directory()
    sync_games_raw()
    sync_games_scores()
    sync_truth()
    sync_tournament_bracket()
    sync_tournament_results()
    sync_tournament_boys_full()
    sync_tournament_boys_with_predictions()
    sync_pick5_participants()
    sync_pick_5_rosters()
    sync_team_of_week_votes()
    sync_milestone_claims()
    sync_milestone_votes()
    print()
    print("All tables synced!")
