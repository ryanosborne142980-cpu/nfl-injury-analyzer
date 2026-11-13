<#
.SYNOPSIS
    Register (or replace) a Windows scheduled task that runs the daily NFL ingestion.

.DESCRIPTION
    Runs `python -m src.ingestion.run_daily` from the repository root once a day. nflverse refreshes injuries
    and rosters at 07:00 UTC, so the default 05:00 local time is after the refresh in every US time zone.
    The task runs as the current user, only while that user is logged on (needed for Windows authentication
    to SQL Server), and catches up on a missed run when the computer next wakes.

    Remove the task with:  Unregister-ScheduledTask -TaskName NflDailyIngestion -Confirm:$false

.EXAMPLE
    .\scripts\register_daily_task.ps1
    .\scripts\register_daily_task.ps1 -At 06:30 -Python C:\path\to\python.exe
#>
param(
    [string]$TaskName = "NflDailyIngestion",
    [string]$At = "05:00",
    [string]$Python = (Get-Command python -ErrorAction Stop).Source,
    [string]$ExtraArgs = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ($Python -like "*\WindowsApps\*") {
    throw "python resolves to the Microsoft Store alias ($Python). Pass -Python with the full path to python.exe."
}

$action = New-ScheduledTaskAction -Execute $Python `
    -Argument "-m src.ingestion.run_daily $ExtraArgs".Trim() `
    -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Description "Daily nflverse extract, quality checks and raw load ($repoRoot)" -Force |
    Out-Null

Write-Host "Registered '$TaskName': daily at $At, running $Python -m src.ingestion.run_daily in $repoRoot"
Write-Host "Run it now with: Start-ScheduledTask -TaskName $TaskName"
