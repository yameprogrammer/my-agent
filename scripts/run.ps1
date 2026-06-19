param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "setup", "init-db", "bootstrap", "test", "admin", "help")]
    [string]$Command = "start"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-VenvPython {
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "Virtual environment not found. Run: .\scripts\run.ps1 setup"
    }
    return $python
}

function Ensure-Setup {
    if (Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe")) {
        return
    }
    Write-Step "Creating virtual environment and installing dependencies..."
    & (Join-Path $PSScriptRoot "setup.ps1")
}

function Invoke-InitDb {
    $python = Get-VenvPython
    Write-Step "Initializing database..."
    & $python main.py --init-db
}

function Invoke-Bootstrap {
    $python = Get-VenvPython
    Write-Step "Bootstrapping demo novel..."
    & $python scripts/bootstrap.py
}

function Invoke-Test {
    $python = Get-VenvPython
    Write-Step "Running tests..."
    & $python -m pytest
}

function Invoke-Admin {
    $python = Get-VenvPython
    $streamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"
    if (-not (Test-Path $streamlit)) {
        throw "streamlit not installed. Run: .\scripts\run.ps1 setup"
    }
    Write-Step "Starting Admin Console (http://localhost:8501)..."
    Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
    & $streamlit run apps/admin/main.py
}

function Show-Help {
    @"
my-agent run script (Windows)

Usage:
  .\scripts\run.ps1 [command]
  .\scripts\run.bat [command]

Commands:
  start      Setup (if needed), init DB, demo novel, launch Admin Console (default)
  setup      Create .venv and install dependencies
  init-db    Initialize SQLite schema
  bootstrap  Create demo novel if the database is empty
  test       Run pytest
  admin      Launch Streamlit Admin Console only
  help       Show this message

Examples:
  .\scripts\run.ps1
  .\scripts\run.ps1 start
  .\scripts\run.ps1 test
"@ | Write-Host
}

switch ($Command) {
    "help" {
        Show-Help
    }
    "setup" {
        & (Join-Path $PSScriptRoot "setup.ps1")
        Write-Host "Setup complete." -ForegroundColor Green
    }
    "init-db" {
        Ensure-Setup
        Invoke-InitDb
    }
    "bootstrap" {
        Ensure-Setup
        Invoke-Bootstrap
    }
    "test" {
        Ensure-Setup
        Invoke-Test
    }
    "admin" {
        Ensure-Setup
        Invoke-Admin
    }
    "start" {
        Ensure-Setup
        Invoke-InitDb
        Invoke-Bootstrap
        Invoke-Admin
    }
}