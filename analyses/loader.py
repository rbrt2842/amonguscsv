"""Load database tables into pandas DataFrames for notebooks."""

from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "amongus.db"


def load_table(table, database=DEFAULT_DATABASE):
    """Return a database table as a DataFrame."""
    allowed = {
        "servers", "players", "player_seasons", "player_voting_stats",
        "player_matches", "common_teammates",
    }
    if table not in allowed:
        raise ValueError(f"Unknown table {table!r}; choose from {sorted(allowed)}")
    with sqlite3.connect(database) as connection:
        return pd.read_sql_query(f"SELECT * FROM {table}", connection)


def load_player_stats(database=DEFAULT_DATABASE):
    """Load one row per player, server, and season."""
    return load_table("player_seasons", database)


def load_voting_stats(database=DEFAULT_DATABASE):
    """Load available aggregate voting records."""
    return load_table("player_voting_stats", database)


def load_match_history(database=DEFAULT_DATABASE):
    """Load the recent match rows saved on each player page."""
    return load_table("player_matches", database)


def load_common_teammates(database=DEFAULT_DATABASE):
    """Load each player's summarized common teammate relationships."""
    return load_table("common_teammates", database)


def load_players_with_voting(database=DEFAULT_DATABASE):
    """Join voting summaries onto player stats; unavailable votes stay null."""
    query = """
        SELECT p.*, v.committed_vote_accuracy_pct, v.eject_accuracy_pct,
               v.skip_abstain_rate_pct, v.ejected_impostor_count,
               v.ejected_crew_count, v.votes_against_impostors, v.skips,
               v.votes_against_crew, v.abstains
        FROM player_seasons AS p
        LEFT JOIN player_voting_stats AS v
          USING (server_name, season, discord_id)
    """
    with sqlite3.connect(database) as connection:
        return pd.read_sql_query(query, connection)
