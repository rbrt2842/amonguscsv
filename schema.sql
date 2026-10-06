PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS servers (
    server_name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS players (
    discord_id TEXT PRIMARY KEY
);

-- One row per player on a server in a tournament/season.
CREATE TABLE IF NOT EXISTS player_seasons (
    server_name TEXT NOT NULL,
    season TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    username TEXT,
    source_file TEXT NOT NULL,
    combined_rank INTEGER,
    combined_mmr INTEGER,
    combined_played_pct REAL,
    combined_wins INTEGER,
    combined_losses INTEGER,
    combined_games INTEGER,
    combined_win_pct REAL,
    combined_win_streak INTEGER,
    combined_win_streak_record INTEGER,
    combined_loss_streak INTEGER,
    combined_loss_streak_record INTEGER,
    crewmate_rank INTEGER,
    crewmate_mmr INTEGER,
    crewmate_played_pct REAL,
    crewmate_wins INTEGER,
    crewmate_losses INTEGER,
    crewmate_games INTEGER,
    crewmate_win_pct REAL,
    crewmate_win_streak INTEGER,
    crewmate_win_streak_record INTEGER,
    crewmate_loss_streak INTEGER,
    crewmate_loss_streak_record INTEGER,
    impostor_rank INTEGER,
    impostor_mmr INTEGER,
    impostor_played_pct REAL,
    impostor_wins INTEGER,
    impostor_losses INTEGER,
    impostor_games INTEGER,
    impostor_win_pct REAL,
    impostor_win_streak INTEGER,
    impostor_win_streak_record INTEGER,
    impostor_loss_streak INTEGER,
    impostor_loss_streak_record INTEGER,
    PRIMARY KEY (server_name, season, discord_id),
    FOREIGN KEY (server_name) REFERENCES servers(server_name),
    FOREIGN KEY (discord_id) REFERENCES players(discord_id)
);

-- Optional aggregate voting record. Pages without voting data have no row here.
CREATE TABLE IF NOT EXISTS player_voting_stats (
    server_name TEXT NOT NULL,
    season TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    committed_vote_accuracy_pct REAL,
    eject_accuracy_pct REAL,
    skip_abstain_rate_pct REAL,
    ejected_impostor_count INTEGER,
    ejected_crew_count INTEGER,
    votes_against_impostors INTEGER,
    skips INTEGER,
    votes_against_crew INTEGER,
    abstains INTEGER,
    PRIMARY KEY (server_name, season, discord_id),
    FOREIGN KEY (server_name, season, discord_id)
        REFERENCES player_seasons(server_name, season, discord_id)
        ON DELETE CASCADE
);

-- Up to ten recent match results recorded on each saved player page.
CREATE TABLE IF NOT EXISTS player_matches (
    server_name TEXT NOT NULL,
    season TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    map TEXT,
    role TEXT,
    win_probability_pct REAL,
    result TEXT,
    mmr_change REAL,
    mmr_pct_of_total REAL,
    PRIMARY KEY (server_name, season, discord_id, match_id),
    FOREIGN KEY (server_name, season, discord_id)
        REFERENCES player_seasons(server_name, season, discord_id)
        ON DELETE CASCADE
);

-- Common teammate summaries are directed from the player page being parsed.
CREATE TABLE IF NOT EXISTS common_teammates (
    server_name TEXT NOT NULL,
    season TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    teammate_discord_id TEXT NOT NULL,
    teammate_rank INTEGER,
    teammate_username TEXT,
    teammate_mmr INTEGER,
    matches_together_count INTEGER,
    matches_together_pct REAL,
    PRIMARY KEY (server_name, season, discord_id, teammate_discord_id),
    FOREIGN KEY (server_name, season, discord_id)
        REFERENCES player_seasons(server_name, season, discord_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_player_seasons_discord
    ON player_seasons(discord_id);
CREATE INDEX IF NOT EXISTS idx_player_seasons_rank
    ON player_seasons(server_name, season, combined_rank);
CREATE INDEX IF NOT EXISTS idx_player_matches_map_role
    ON player_matches(map, role);
CREATE INDEX IF NOT EXISTS idx_common_teammates_target
    ON common_teammates(teammate_discord_id);
