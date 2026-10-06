# Among Us stats explorer

This project turns saved Ranked Among Us player pages into a SQLite database
and a Jupyter notebook workspace for exploring the stats and making graphs.
The repository includes a built database snapshot, so the notebook can be used
without downloading the original HTML archive. The old CSV exports are archived
in [`old/`](old/).

## Open the notebook

Open this project folder in VS Code, then open
[`analyses/analysis.ipynb`](analyses/analysis.ipynb). Select the
**Python (amonguscsv)** kernel and run the first cell. It loads:

- `players`: one row per player, server, and season, including MMR, wins,
  losses, games, rank, and streaks.
- `players_with_voting`: the same rows with optional aggregate voting stats.
  Voting columns are empty for players whose pages had no voting data.

The database is available as `amongus.db` in the project folder. The project
environment and named kernel are already set up in this checkout. For a fresh
setup, run these commands from the project folder:

```sh
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m ipykernel install --prefix "$PWD/venv" \
  --name amonguscsv --display-name "Python (amonguscsv)"
```

VS Code needs its Python and Jupyter extensions enabled to run `.ipynb` files.

## Ask an LLM for a graph

After the first notebook cell runs, ask your coding assistant to add a new
notebook cell. Name the DataFrame, filters, calculation, and chart you want.
For example:

> Using `players`, make a scatter plot for Among Us League Season 5. Put
> `combined_mmr` on the x-axis and win rate on the y-axis. Calculate win rate
> from `combined_wins / (combined_wins + combined_losses) * 100`; omit rows
> with no games or missing MMR. Add a title and axis labels.

You can inspect what’s available with:

```python
players.columns.tolist()
players[["server_name", "season"]].drop_duplicates().sort_values(
    ["server_name", "season"]
)
```

The notebook loads the percentages recorded on the site, but you can calculate
your own from the underlying counts when you prefer a different formula.

## Rebuild the database

The saved database is included in Git. The original HTML archive is not. To
rebuild from source, put `aznbot.zip` in the project folder or use a directory
of extracted HTML pages, then run:

```sh
venv/bin/python build_database.py aznbot.zip
```

The importer reads the ZIP directly without extracting it. It updates matching
records in an existing database; to rebuild from scratch, remove `amongus.db`
first. To use an HTML directory or choose another output path:

```sh
venv/bin/python build_database.py /path/to/html_pages --output /path/to/amongus.db
```

## Data available to explore

The database schema is in [`schema.sql`](schema.sql). The notebook loader
([`analyses/loader.py`](analyses/loader.py)) provides these DataFrames:

| Loader | Rows describe |
| --- | --- |
| `load_player_stats()` | Player stats for a server and season |
| `load_voting_stats()` | Available aggregate voting totals and ratios |
| `load_match_history()` | Recent match results listed on saved pages |
| `load_common_teammates()` | Teammate summaries listed on saved pages |
| `load_players_with_voting()` | Player stats joined with optional voting data |

For example, load the other tables in a notebook cell with:

```python
from analyses.loader import (
    load_voting_stats,
    load_match_history,
    load_common_teammates,
)

votes = load_voting_stats()
matches = load_match_history()
teammates = load_common_teammates()
```
