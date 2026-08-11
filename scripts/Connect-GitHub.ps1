param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$RepositoryUrl
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw '未找到 Git，请先安装 Git。'
}

git -C $repositoryRoot remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    git -C $repositoryRoot remote set-url origin $RepositoryUrl
} else {
    git -C $repositoryRoot remote add origin $RepositoryUrl
}

git -C $repositoryRoot branch -M main
git -C $repositoryRoot remote -v
Write-Host '远程仓库已绑定。首次推送请执行：git -C "' $repositoryRoot '" push -u origin main'
