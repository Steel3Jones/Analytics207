from __future__ import annotations

import pandas as pd
import streamlit as st

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
    spacer,
    TableColumn,
    render_html_table,
    render_performance_strip,
)


def render_body() -> None:
    spacer(1)

    df = pd.DataFrame(
        [
            {"Date": "Feb 01", "Home": "Team A", "Away": "Team B", "Conf": 0.74, "HomeScore": 62, "AwayScore": 55, "Correct": True},
            {"Date": "Feb 02", "Home": "Team C", "Away": "Team D", "Conf": 0.58, "HomeScore": 0, "AwayScore": 0, "Correct": None},
        ]
    )

    total_games = len(df)
    played_games = int(((df["HomeScore"] + df["AwayScore"]) > 0).sum())
    correct_games = int(pd.to_numeric(df["Correct"], errors="coerce").fillna(0).sum())

    render_performance_strip(total_games, played_games, correct_games, label="Example Performance")

    cols = [
        TableColumn("Date", "Date", kind="mono"),
        TableColumn("Home", "Home"),
        TableColumn("Away", "Away"),
        TableColumn("Confidence", "Conf", kind="pill_conf"),
        TableColumn("Final", "Final", kind="final_score"),
        TableColumn("Result", "Correct", kind="result_icon"),
    ]

    render_html_table(df, cols, title="Example Table")


def main() -> None:
    apply_global_layout_tweaks()
    render_logo()
    render_page_header(title="New Page", definition="", subtitle="")
    render_body()
    spacer(2)
    render_footer()


if __name__ == "__main__":
    main()
