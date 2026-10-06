#!/usr/bin/env python3
"""Parse saved Ranked Among Us pages into a queryable SQLite database."""

import argparse
import re
import sqlite3
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from extract_player_stats import parse_page
from extract_match_history import extract_match_history
from extract_teammates import extract_teammates


ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "schema.sql"
ROLE_FIELDS = (
    ("rank", "rank", int),
    ("mmr", "mmr", int),
    ("played_pct", "played_pct", float),
    ("wins", "wins", int),
    ("losses", "losses", int),
    ("games", "games", int),
    ("win_pct", "win_pct", float),
    ("win_streak", "win_streak", int),
    ("win_streak_record", "win_record_streak", int),
    ("loss_streak", "loss_streak", int),
    ("loss_streak_record", "loss_record_streak", int),
)
VOTING_FIELDS = (
    "committed_vote_accuracy_pct",
    "eject_accuracy_pct",
    "skip_abstain_rate_pct",
    "ejected_impostor_count",
    "ejected_crew_count",
    "votes_against_impostors",
    "skips",
    "votes_against_crew",
    "abstains",
)
VOTING_PATTERNS = {
    "committed_vote_accuracy_pct": r"([\d.]+)%\s*accuracy on committ?ed votes",
    "eject_accuracy_pct": r"([\d.]+)%\s*accuracy on ejects",
    "skip_abstain_rate_pct": r"([\d.]+)%\s*used on skips and abstains",
    "ejected_impostor_count": r"(\d+)\s*resulted eject of impostor",
    "ejected_crew_count": r"(\d+)\s*resulted eject of crew",
    "votes_against_impostors": r"(\d+)\s*against impostors",
    "skips": r"(\d+)\s*skips",
    "votes_against_crew": r"(\d+)\s*against crew",
    "abstains": r"(\d+)\s*abstained",
}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


def parse_voting_stats(html):
    text_parser = VisibleText()
    text_parser.feed(html)
    text = re.sub(r"\s+", " ", " ".join(text_parser.parts)).lower()
    result = {}
    for field, pattern in VOTING_PATTERNS.items():
        match = re.search(pattern, text, re.I)
        if match:
            result[field] = float(match.group(1)) if field.endswith("_pct") else int(match.group(1))
    return result


def discord_id_from_filename(filename):
    match = re.search(r"(\d{17,20})(?=\.html$)", Path(filename).name, re.I)
    return match.group(1) if match else None


def records_for_page(html, source_file):
    server, tournament, _season_number, page_id, username, _avatar, roles = parse_page(html)
    discord_id = discord_id_from_filename(source_file) or page_id
    if not discord_id:
        return None, None

    record = {
        "server_name": server or "Unknown",
        "season": tournament or "Unknown",
        "discord_id": discord_id,
        "username": username or "Unknown",
        "source_file": str(source_file),
    }
    for role in ("combined", "crewmate", "impostor"):
        values = roles[role]
        for output_name, source_name, convert in ROLE_FIELDS:
            raw = values.get(source_name, "")
            if output_name == "games" and not raw:
                wins, losses = values.get("wins", ""), values.get("losses", "")
                raw = str(int(wins) + int(losses)) if wins.isdigit() and losses.isdigit() else ""
            try:
                record[f"{role}_{output_name}"] = convert(raw) if raw != "" else None
            except (TypeError, ValueError):
                record[f"{role}_{output_name}"] = None

    voting = parse_voting_stats(html)
    if voting:
        voting_record = {
            "server_name": record["server_name"],
            "season": record["season"],
            "discord_id": discord_id,
        }
        voting_record.update({name: voting.get(name) for name in VOTING_FIELDS})
    else:
        voting_record = None
    return record, voting_record


def iter_pages(source):
    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                if not info.is_dir() and info.filename.lower().endswith(".html"):
                    with archive.open(info) as stream:
                        yield info.filename, stream.read().decode("utf-8", errors="replace")
        return
    if source.is_file() and source.suffix.lower() == ".html":
        yield source.name, source.read_text(encoding="utf-8", errors="replace")
        return
    if source.is_dir():
        for path in sorted(source.rglob("*.html")):
            yield str(path.relative_to(source)), path.read_text(encoding="utf-8", errors="replace")
        return
    raise ValueError(f"Input must be an HTML file, directory, or ZIP archive: {source}")


def insert_record(connection, table, record):
    columns = list(record)
    placeholders = ", ".join("?" for _ in columns)
    names = ", ".join(f'"{name}"' for name in columns)
    mode = "OR IGNORE" if table in {"servers", "players"} else "OR REPLACE"
    connection.execute(
        f"INSERT {mode} INTO {table} ({names}) VALUES ({placeholders})",
        [record[name] for name in columns],
    )


def build_database(source, output):
    connection = sqlite3.connect(output)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    page_count = 0
    voting_count = 0
    skipped = 0
    with connection:
        for source_file, html in iter_pages(source):
            player, voting = records_for_page(html, source_file)
            if player is None:
                skipped += 1
                continue
            insert_record(connection, "servers", {"server_name": player["server_name"]})
            insert_record(connection, "players", {"discord_id": player["discord_id"]})
            insert_record(connection, "player_seasons", player)
            if voting:
                insert_record(connection, "player_voting_stats", voting)
                voting_count += 1
            for match in extract_match_history(html):
                match_record = {
                    "server_name": player["server_name"],
                    "season": player["season"],
                    "discord_id": player["discord_id"],
                    "match_id": match["match_id"],
                    "map": match["map"],
                    "role": match["role"],
                    "win_probability_pct": float(match["win_probability_pct"]),
                    "result": match["result"],
                    "mmr_change": float(match["mmr_change"]),
                    "mmr_pct_of_total": float(match["mmr_pct_of_total"]) if match["mmr_pct_of_total"] else None,
                }
                insert_record(connection, "player_matches", match_record)
            for teammate in extract_teammates(html):
                teammate_record = {
                    "server_name": player["server_name"],
                    "season": player["season"],
                    "discord_id": player["discord_id"],
                    "teammate_discord_id": teammate["teammate_discord_id"],
                    "teammate_rank": int(teammate["teammate_rank"]),
                    "teammate_username": teammate["teammate_username"],
                    "teammate_mmr": int(teammate["teammate_mmr"]),
                    "matches_together_count": int(teammate["matches_together_count"]),
                    "matches_together_pct": float(teammate["matches_together_pct"]),
                }
                insert_record(connection, "common_teammates", teammate_record)
            page_count += 1
    connection.close()
    return page_count, voting_count, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="HTML file, directory, or ZIP of saved player pages")
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "amongus.db")
    args = parser.parse_args()
    pages, voting, skipped = build_database(args.input, args.output)
    print(f"Imported {pages} player pages ({voting} with voting data); skipped {skipped} without a Discord ID.")
    print(f"Database: {args.output}")


if __name__ == "__main__":
    main()
