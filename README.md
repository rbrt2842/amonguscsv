# Among Us stats archive

This project parses saved Ranked Among Us player pages into a SQLite database.
The database keeps a player-season row keyed by server, tournament/season, and
Discord ID. Aggregate voting statistics live in a separate optional table, so
players whose pages have no voting data are still represented normally.

## Build the database

The importer accepts a directory of saved HTML pages, one HTML page, or the
large ZIP archive directly. It does not extract the ZIP to disk.

```sh
python3 -m pip install -r requirements.txt
python3 build_database.py aznbot.zip
```

This creates `amongus.db` next to the scripts. To use an extracted directory or
choose a different output path:

```sh
python3 build_database.py /path/to/html_pages --output /path/to/amongus.db
```

The SQLite schema is in `schema.sql`. The two main analysis tables are:

- `player_seasons`: ranks, MMR, games, wins/losses, win rates, and streaks for
  each server-season-player combination.
- `player_voting_stats`: available aggregate vote accuracy and count metrics,
  with the same composite key. A player without voting data has no row here.
- `player_matches`: recent match rows linked to their player's server and season.
- `common_teammates`: summarized teammate relationships from each player page.

`source_file` preserves the archive path for tracing a database row back to its
HTML page. Discord IDs are stored as text to preserve them exactly.

## Jupyter

Install the requirements in the notebook's Python environment, start Jupyter
from this project directory, and load the tables:

```python
from analyses.loader import (
    load_player_stats,
    load_voting_stats,
    load_match_history,
    load_common_teammates,
    load_players_with_voting,
)

players = load_player_stats()
votes = load_voting_stats()
players_with_votes = load_players_with_voting()
matches = load_match_history()
teammates = load_common_teammates()
```

The loader returns pandas DataFrames. `analyses/analysis.ipynb` has a starter
query and chart to build on.
