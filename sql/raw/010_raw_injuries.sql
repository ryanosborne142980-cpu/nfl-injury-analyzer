-- Weekly injury reports (one row per player per team per week).
-- Schema drift: 2025+ files add season_type and drop date_modified, so both are nullable here.
-- All source columns are loaded as text. Types are applied in the staging layer.
-- Columns come from the real nflverse file headers; tests/unit/test_raw_ddl.py keeps them in sync.

IF OBJECT_ID('raw.injuries', 'U') IS NULL
BEGIN
    CREATE TABLE raw.injuries (
        [_batch_id]                  INT NOT NULL,
        [_source_file]               NVARCHAR(260) NOT NULL,
        [_loaded_at]                 DATETIME2(0) NOT NULL CONSTRAINT DF_raw_injuries_loaded_at DEFAULT SYSUTCDATETIME(),
        [season]                     NVARCHAR(500) NULL,
        [season_type]                NVARCHAR(500) NULL,
        [game_type]                  NVARCHAR(500) NULL,
        [team]                       NVARCHAR(500) NULL,
        [week]                       NVARCHAR(500) NULL,
        [gsis_id]                    NVARCHAR(500) NULL,
        [position]                   NVARCHAR(500) NULL,
        [full_name]                  NVARCHAR(500) NULL,
        [first_name]                 NVARCHAR(500) NULL,
        [last_name]                  NVARCHAR(500) NULL,
        [report_primary_injury]      NVARCHAR(500) NULL,
        [report_secondary_injury]    NVARCHAR(500) NULL,
        [report_status]              NVARCHAR(500) NULL,
        [practice_primary_injury]    NVARCHAR(500) NULL,
        [practice_secondary_injury]  NVARCHAR(500) NULL,
        [practice_status]            NVARCHAR(500) NULL,
        [date_modified]              NVARCHAR(500) NULL
    );
    CREATE INDEX IX_raw_injuries_batch ON raw.injuries ([_batch_id]);
END;
