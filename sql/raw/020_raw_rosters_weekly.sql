-- Weekly rosters (one row per player per team per week, all roster statuses).
-- All source columns are loaded as text. Types are applied in the staging layer.
-- Columns come from the real nflverse file headers; tests/unit/test_raw_ddl.py keeps them in sync.

IF OBJECT_ID('raw.rosters_weekly', 'U') IS NULL
BEGIN
    CREATE TABLE raw.rosters_weekly (
        [_batch_id]                INT NOT NULL,
        [_source_file]             NVARCHAR(260) NOT NULL,
        [_loaded_at]               DATETIME2(0) NOT NULL CONSTRAINT DF_raw_rosters_weekly_loaded_at DEFAULT SYSUTCDATETIME(),
        [season]                   NVARCHAR(500) NULL,
        [team]                     NVARCHAR(500) NULL,
        [position]                 NVARCHAR(500) NULL,
        [depth_chart_position]     NVARCHAR(500) NULL,
        [jersey_number]            NVARCHAR(500) NULL,
        [status]                   NVARCHAR(500) NULL,
        [full_name]                NVARCHAR(500) NULL,
        [first_name]               NVARCHAR(500) NULL,
        [last_name]                NVARCHAR(500) NULL,
        [birth_date]               NVARCHAR(500) NULL,
        [height]                   NVARCHAR(500) NULL,
        [weight]                   NVARCHAR(500) NULL,
        [college]                  NVARCHAR(500) NULL,
        [gsis_id]                  NVARCHAR(500) NULL,
        [espn_id]                  NVARCHAR(500) NULL,
        [sportradar_id]            NVARCHAR(500) NULL,
        [yahoo_id]                 NVARCHAR(500) NULL,
        [rotowire_id]              NVARCHAR(500) NULL,
        [pff_id]                   NVARCHAR(500) NULL,
        [pfr_id]                   NVARCHAR(500) NULL,
        [fantasy_data_id]          NVARCHAR(500) NULL,
        [sleeper_id]               NVARCHAR(500) NULL,
        [years_exp]                NVARCHAR(500) NULL,
        [headshot_url]             NVARCHAR(1000) NULL,
        [ngs_position]             NVARCHAR(500) NULL,
        [week]                     NVARCHAR(500) NULL,
        [game_type]                NVARCHAR(500) NULL,
        [status_description_abbr]  NVARCHAR(500) NULL,
        [football_name]            NVARCHAR(500) NULL,
        [esb_id]                   NVARCHAR(500) NULL,
        [gsis_it_id]               NVARCHAR(500) NULL,
        [smart_id]                 NVARCHAR(500) NULL,
        [entry_year]               NVARCHAR(500) NULL,
        [rookie_year]              NVARCHAR(500) NULL,
        [draft_club]               NVARCHAR(500) NULL,
        [draft_number]             NVARCHAR(500) NULL
    );
    CREATE INDEX IX_raw_rosters_weekly_batch ON raw.rosters_weekly ([_batch_id]);
END;
