param(
  [string]$ProjectRoot = (Join-Path $PSScriptRoot "..")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$resolvedProjectRoot = (Resolve-Path $ProjectRoot).Path
$startupDir = [Environment]::GetFolderPath("Startup")
$launcherPath = Join-Path $startupDir "automation-core-startup.cmd"
$startScriptPath = (Resolve-Path (Join-Path $PSScriptRoot "start-automation-core.ps1")).Path
$envPath = Join-Path $resolvedProjectRoot ".env"
$hostPort = "4313"

if (Test-Path $envPath) {
  foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^\s*HOST_PORT\s*=\s*(.+?)\s*$') {
      $hostPort = $matches[1].Trim('"')
      break
    }
  }
}

$content = @(
  "@echo off",
  "PowerShell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScriptPath`""
)

Set-Content -LiteralPath $launcherPath -Value $content -Encoding ASCII

Write-Output "Installed startup launcher:"
Write-Output $launcherPath
Write-Output ""
Write-Output "automation-core will now start automatically at login."
Write-Output "Dashboard URL: http://127.0.0.1:$hostPort/"
