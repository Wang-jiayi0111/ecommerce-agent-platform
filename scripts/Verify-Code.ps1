$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot

Push-Location "$repositoryRoot/backend"
try {
    python -m ruff check app tests
    python -m ruff format --check app tests
    python -m pytest -q
} finally {
    Pop-Location
}

Push-Location "$repositoryRoot/frontend"
try {
    npm.cmd run lint
    npm.cmd run format:check
    npm.cmd run build
} finally {
    Pop-Location
}
