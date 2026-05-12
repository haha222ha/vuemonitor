param(
    [string]$EnvFile = ".env.production",
    [string]$ComposeFile = "docker-compose.yml",
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$DeployDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $DeployDir

function Write-Step {
    param([string]$Message)
    Write-Host "`n>>> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  OK: $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  FAIL: $Message" -ForegroundColor Red
}

function Test-Command {
    param([string]$Name)
    try {
        Get-Command $Name -ErrorAction Stop | Out-Null
        Write-Success "$Name found"
        return $true
    } catch {
        Write-Fail "$Name not found"
        return $false
    }
}

function Test-Port {
    param([int]$Port)
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        Write-Success "Port $Port available"
        return $true
    } catch {
        Write-Fail "Port $Port in use"
        return $false
    }
}

$allPassed = $true

Write-Step "Step 1: Prerequisites Check"
$dockerOk = Test-Command "docker"
$composeOk = Test-Command "docker-compose"
if (-not $dockerOk -or -not $composeOk) {
    Write-Fail "Docker and docker-compose are required"
    $allPassed = $false
}

Write-Step "Step 2: Environment File Check"
$envPath = Join-Path $ProjectDir $EnvFile
if (Test-Path $envPath) {
    Write-Success "Environment file found: $envPath"
    $envContent = Get-Content $envPath
    $requiredVars = @("DB_HOST", "DB_PASSWORD", "JWT_SECRET", "ENCRYPTION_KEY", "REDIS_HOST")
    foreach ($var in $requiredVars) {
        $found = $envContent | Where-Object { $_ -match "^$var=" -and $_ -notmatch "=your_" -and $_ -notmatch "=changeme" }
        if ($found) {
            Write-Success "$var is configured"
        } else {
            Write-Fail "$var is missing or using default value"
            $allPassed = $false
        }
    }
} else {
    Write-Fail "Environment file not found: $envPath"
    $allPassed = $false
}

Write-Step "Step 3: Port Availability Check"
$portsOk = $true
$portsOk = $portsOk -and (Test-Port 8000)
$portsOk = $portsOk -and (Test-Port 5432)
$portsOk = $portsOk -and (Test-Port 6379)
if (-not $portsOk) { $allPassed = $false }

Write-Step "Step 4: Docker Build"
if (-not $SkipBuild) {
    Push-Location $ProjectDir
    try {
        docker-compose -f $ComposeFile build --no-cache 2>&1 | ForEach-Object {
            if ($Verbose) { Write-Host $_ }
        }
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker images built successfully"
        } else {
            Write-Fail "Docker build failed"
            $allPassed = $false
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Success "Build skipped"
}

Write-Step "Step 5: Start Services"
Push-Location $ProjectDir
try {
    docker-compose -f $ComposeFile up -d 2>&1 | ForEach-Object {
        if ($Verbose) { Write-Host $_ }
    }
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Services started"
    } else {
        Write-Fail "Failed to start services"
        $allPassed = $false
    }
} finally {
    Pop-Location
}

Write-Step "Step 6: Wait for Services"
Write-Host "  Waiting 30 seconds for services to initialize..."
Start-Sleep -Seconds 30

Write-Step "Step 7: Health Checks"
try {
    $healthResp = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10 -UseBasicParsing
    if ($healthResp.StatusCode -eq 200) {
        Write-Success "Server health check passed"
    } else {
        Write-Fail "Server health check returned $($healthResp.StatusCode)"
        $allPassed = $false
    }
} catch {
    Write-Fail "Server health check failed: $_"
    $allPassed = $false
}

try {
    $apiResp = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 10 -UseBasicParsing
    if ($apiResp.StatusCode -eq 200) {
        Write-Success "API health check passed"
    } else {
        Write-Fail "API health check returned $($apiResp.StatusCode)"
        $allPassed = $false
    }
} catch {
    Write-Fail "API health check failed: $_"
    $allPassed = $false
}

Write-Step "Step 8: Database Migration"
Push-Location (Join-Path $ProjectDir "server")
try {
    docker-compose -f (Join-Path $ProjectDir $ComposeFile) exec server alembic upgrade head 2>&1 | ForEach-Object {
        if ($Verbose) { Write-Host $_ }
    }
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Database migration completed"
    } else {
        Write-Fail "Database migration failed"
        $allPassed = $false
    }
} catch {
    Write-Fail "Database migration error: $_"
    $allPassed = $false
} finally {
    Pop-Location
}

Write-Step "Step 9: API Integration Tests"
if (-not $SkipTests) {
    Push-Location (Join-Path $ProjectDir "server")
    try {
        python -m pytest tests/test_api_integration.py -v --tb=short 2>&1 | ForEach-Object {
            if ($Verbose) { Write-Host $_ }
        }
        if ($LASTEXITCODE -eq 0) {
            Write-Success "API integration tests passed"
        } else {
            Write-Fail "API integration tests failed"
            $allPassed = $false
        }
    } catch {
        Write-Fail "API integration tests error: $_"
        $allPassed = $false
    } finally {
        Pop-Location
    }
} else {
    Write-Success "Tests skipped"
}

Write-Step "Step 10: Docker Service Status"
Push-Location $ProjectDir
try {
    docker-compose -f $ComposeFile ps 2>&1 | ForEach-Object { Write-Host "  $_" }
} finally {
    Pop-Location
}

Write-Step "Deployment Verification Result"
if ($allPassed) {
    Write-Host "`n  ALL CHECKS PASSED - Production deployment verified!" -ForegroundColor Green
} else {
    Write-Host "`n  SOME CHECKS FAILED - Review errors above" -ForegroundColor Red
}

Write-Host "`n  To stop services: docker-compose -f $ComposeFile down"
Write-Host "  To view logs: docker-compose -f $ComposeFile logs -f"
