-- Player master, all seasons in one file (reloaded in full each run).
-- All source columns are loaded as text. Types are applied in the staging layer.
-- Columns come from the real nflverse file headers; tests/unit/test_raw_ddl.py keeps them in sync.

IF OBJECT_ID('raw.players', 'U') IS NULL
BEGIN
    CREATE TABLE raw.players (
        [_batch_id]                     INT NOT NULL,
        [_source_file]                  NVARCHAR(260) NOT NULL,
        [_loaded_at]                    DATETIME2(0) NOT NULL CONSTRAINT DF_raw_players_loaded_at DEFAULT SYSUTCDATETIME(),
        [gsis_id]                       NVARCHAR(500) NULL,
        [display_name]                  NVARCHAR(500) NULL,
        [common_first_name]             NVARCHAR(500) NULL,
        [first_name]                    NVARCHAR(500) NULL,
        [last_name]                     NVARCHAR(500) NULL,
        [short_name]                    NVARCHAR(500) NULL,
        [football_name]                 NVARCHAR(500) NULL,
        [suffix]                        NVARCHAR(500) NULL,
        [esb_id]                        NVARCHAR(500) NULL,
        [nfl_id]                        NVARCHAR(500) NULL,
        [pfr_id]                        NVARCHAR(500) NULL,
        [pff_id]                        NVARCHAR(500) NULL,
        [otc_id]                        NVARCHAR(500) NULL,
        [espn_id]                       NVARCHAR(500) NULL,
        [smart_id]                      NVARCHAR(500) NULL,
        [birth_date]                    NVARCHAR(500) NULL,
        [position_group]                NVARCHAR(500) NULL,
        [position]                      NVARCHAR(500) NULL,
        [ngs_position_group]            NVARCHAR(500) NULL,
        [ngs_position]                  NVARCHAR(500) NULL,
        [height]                        NVARCHAR(500) NULL,
        [weight]                        NVARCHAR(500) NULL,
        [headshot]                      NVARCHAR(1000) NULL,
        [college_name]                  NVARCHAR(500) NULL,
        [college_conference]            NVARCHAR(500) NULL,
        [jersey_number]                 NVARCHAR(500) NULL,
        [rookie_season]                 NVARCHAR(500) NULL,
        [last_season]                   NVARCHAR(500) NULL,
        [latest_team]                   NVARCHAR(500) NULL,
        [status]                        NVARCHAR(500) NULL,
        [ngs_status]                    NVARCHAR(500) NULL,
        [ngs_status_short_description]  NVARCHAR(500) NULL,
        [years_of_experience]           NVARCHAR(500) NULL,
        [pff_position]                  NVARCHAR(500) NULL,
        [pff_status]                    NVARCHAR(500) NULL,
        [draft_year]                    NVARCHAR(500) NULL,
        [draft_round]                   NVARCHAR(500) NULL,
        [draft_pick]                    NVARCHAR(500) NULL,
        [draft_team]                    NVARCHAR(500) NULL
    );
    CREATE INDEX IX_raw_players_batch ON raw.players ([_batch_id]);
END;
