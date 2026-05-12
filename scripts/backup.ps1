$ErrorActionPreference = "Stop"

$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "vuemonitor" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "saas_user" }
$BACKUP_DIR = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { ".\backups" }
$RETENTION_DAYS = if ($env:RETENTION_DAYS) { [int]$env:RETENTION_DAYS } else { 7 }

if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
}

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_FILE = Join-Path $BACKUP_DIR "vuemonitor_${TIMESTAMP}.dump"

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting backup: $BACKUP_FILE"

$env:PGPASSWORD = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "saas_pass" }

pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -Fc $DB_NAME -f $BACKUP_FILE

if ($LASTEXITCODE -eq 0) {
    $SIZE = (Get-Item $BACKUP_FILE).Length / 1MB
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Backup completed: $BACKUP_FILE ($([math]::Round($SIZE, 2)) MB)"

    $CUTOFF = (Get-Date).AddDays(-$RETENTION_DAYS)
    Get-ChildItem -Path $BACKUP_DIR -Filter "vuemonitor_*.dump" |
        Where-Object { $_.LastWriteTime -lt $CUTOFF } |
        ForEach-Object {
            Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Removing old backup: $($_.Name)"
            Remove-Item $_.FullName -Force
        }
} else {
    Write-Error "Backup failed with exit code $LASTEXITCODE"
}

Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
