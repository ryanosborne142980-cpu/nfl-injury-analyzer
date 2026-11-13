-- Create the layer schemas. Safe to re-run.
-- The database itself (database.name in config) must already exist.

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'raw')     EXEC('CREATE SCHEMA raw');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'staging') EXEC('CREATE SCHEMA staging');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dim')     EXEC('CREATE SCHEMA dim');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'fact')    EXEC('CREATE SCHEMA fact');
