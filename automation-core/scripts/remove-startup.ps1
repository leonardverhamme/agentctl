Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$startupDir = [Environment]::GetFolderPath("Startup")
$launcherPath = Join-Path $startupDir "automation-core-startup.cmd"

if (Test-Path $launcherPath) {
  Remove-Item -LiteralPath $launcherPath -Force
  Write-Output "Removed startup launcher:"
  Write-Output $launcherPath
} else {
  Write-Output "No startup launcher was installed."
}
