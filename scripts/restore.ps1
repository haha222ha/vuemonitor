$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,

    [string]$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" },
    [string]$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" },
    [string]$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "vuemonitor" },
    [string]$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "saas_user" }
)

if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found: $BackupFile"
    exit 1
}

$env:PGPASSWORD = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "saas_pass" }

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Restoring from: $BackupFile"
Write-Host "  Target: ${DB_HOST}:${DB_PORT}/${DB_NAME}"

$CONFIRM = Read-Host "This will DROP existing data and restore from backup. Continue? (yes/no)"
if ($CONFIRM -ne "yes") {
    Write-Host "Restore cancelled."
    exit 0
}

pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c --if-exists $BackupFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Restore completed successfully"
} else {
    Write-Error "Restore failed with exit code $LASTEXITCODE"
}

Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
