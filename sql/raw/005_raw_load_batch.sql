-- One row per file load. Supports row-count reconciliation and lineage back to the source file.

IF OBJECT_ID('raw.load_batch', 'U') IS NULL
BEGIN
    CREATE TABLE raw.load_batch (
        batch_id      INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_raw_load_batch PRIMARY KEY,
        dataset       NVARCHAR(50)   NOT NULL,
        source_file   NVARCHAR(260)  NOT NULL,
        file_sha256   CHAR(64)       NOT NULL,
        rows_in_file  INT            NOT NULL,
        rows_loaded   INT            NULL,
        status        NVARCHAR(20)   NOT NULL,   -- running | succeeded | failed
        started_at    DATETIME2(0)   NOT NULL CONSTRAINT DF_raw_load_batch_started DEFAULT SYSUTCDATETIME(),
        finished_at   DATETIME2(0)   NULL,
        error         NVARCHAR(4000) NULL
    );
END;
