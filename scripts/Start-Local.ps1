$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$backendLog = Join-Path $repositoryRoot "work\api.log"
$backendErrorLog = Join-Path $repositoryRoot "work\api.error.log"
$frontendLog = Join-Path $repositoryRoot "work\web.log"
$frontendErrorLog = Join-Path $repositoryRoot "work\web.error.log"

New-Item -ItemType Directory -Force -Path (Join-Path $repositoryRoot "work") | Out-Null

Start-Process -FilePath python -WorkingDirectory (Join-Path $repositoryRoot "backend") `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrorLog -WindowStyle Hidden

Start-Process -FilePath npm.cmd -WorkingDirectory (Join-Path $repositoryRoot "frontend") `
    -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173" `
    -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErrorLog -WindowStyle Hidden

Write-Host "API: http://127.0.0.1:8000/docs"
Write-Host "Web: http://127.0.0.1:5173"
