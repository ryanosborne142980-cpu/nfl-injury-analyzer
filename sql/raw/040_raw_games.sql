-- Game schedule and results, all seasons in one file (reloaded in full each run).
-- Has stadium id/name, roof and surface, but no city, state, latitude or longitude.
-- All source columns are loaded as text. Types are applied in the staging layer.
-- Columns come from the real nflverse file headers; tests/unit/test_raw_ddl.py keeps them in sync.

IF OBJECT_ID('raw.games', 'U') IS NULL
BEGIN
    CREATE TABLE raw.games (
        [_batch_id]         INT NOT NULL,
        [_source_file]      NVARCHAR(260) NOT NULL,
        [_loaded_at]        DATETIME2(0) NOT NULL CONSTRAINT DF_raw_games_loaded_at DEFAULT SYSUTCDATETIME(),
        [game_id]           NVARCHAR(500) NULL,
        [season]            NVARCHAR(500) NULL,
        [game_type]         NVARCHAR(500) NULL,
        [week]              NVARCHAR(500) NULL,
        [gameday]           NVARCHAR(500) NULL,
        [weekday]           NVARCHAR(500) NULL,
        [gametime]          NVARCHAR(500) NULL,
        [away_team]         NVARCHAR(500) NULL,
        [away_score]        NVARCHAR(500) NULL,
        [home_team]         NVARCHAR(500) NULL,
        [home_score]        NVARCHAR(500) NULL,
        [location]          NVARCHAR(500) NULL,
        [result]            NVARCHAR(500) NULL,
        [total]             NVARCHAR(500) NULL,
        [overtime]          NVARCHAR(500) NULL,
        [old_game_id]       NVARCHAR(500) NULL,
        [gsis]              NVARCHAR(500) NULL,
        [nfl_detail_id]     NVARCHAR(500) NULL,
        [pfr]               NVARCHAR(500) NULL,
        [pff]               NVARCHAR(500) NULL,
        [espn]              NVARCHAR(500) NULL,
        [ftn]               NVARCHAR(500) NULL,
        [away_rest]         NVARCHAR(500) NULL,
        [home_rest]         NVARCHAR(500) NULL,
        [away_moneyline]    NVARCHAR(500) NULL,
        [home_moneyline]    NVARCHAR(500) NULL,
        [spread_line]       NVARCHAR(500) NULL,
        [away_spread_odds]  NVARCHAR(500) NULL,
        [home_spread_odds]  NVARCHAR(500) NULL,
        [total_line]        NVARCHAR(500) NULL,
        [under_odds]        NVARCHAR(500) NULL,
        [over_odds]         NVARCHAR(500) NULL,
        [div_game]          NVARCHAR(500) NULL,
        [roof]              NVARCHAR(500) NULL,
        [surface]           NVARCHAR(500) NULL,
        [temp]              NVARCHAR(500) NULL,
        [wind]              NVARCHAR(500) NULL,
        [away_qb_id]        NVARCHAR(500) NULL,
        [home_qb_id]        NVARCHAR(500) NULL,
        [away_qb_name]      NVARCHAR(500) NULL,
        [home_qb_name]      NVARCHAR(500) NULL,
        [away_coach]        NVARCHAR(500) NULL,
        [home_coach]        NVARCHAR(500) NULL,
        [referee]           NVARCHAR(500) NULL,
        [stadium_id]        NVARCHAR(500) NULL,
        [stadium]           NVARCHAR(500) NULL
    );
    CREATE INDEX IX_raw_games_batch ON raw.games ([_batch_id]);
END;
