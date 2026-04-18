param(
  [string]$ProjectRoot = (Join-Path $PSScriptRoot ".."),
  [int]$DockerWaitSeconds = 120,
  [int]$HealthWaitSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

$resolvedProjectRoot = (Resolve-Path $ProjectRoot).Path
$logDir = Join-Path $resolvedProjectRoot "output\startup"
$null = New-Item -ItemType Directory -Force -Path $logDir
$logFile = Join-Path $logDir "automation-core-startup.log"

function Write-Log {
  param([string]$Message)

  $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -LiteralPath $logFile -Value "[$timestamp] $Message"
}

function Get-HostPort {
  param([string]$EnvFilePath)

  $defaultPort = "4313"
  if (-not (Test-Path $EnvFilePath)) {
    return $defaultPort
  }

  foreach ($line in Get-Content -LiteralPath $EnvFilePath) {
    if ($line -match '^\s*HOST_PORT\s*=\s*(.+?)\s*$') {
      return $matches[1].Trim('"')
    }
  }

  return $defaultPort
}

Set-Location $resolvedProjectRoot

$docker = (Get-Command docker -ErrorAction Stop).Source
$envFilePath = Join-Path $resolvedProjectRoot ".env"
$hostPort = Get-HostPort -EnvFilePath $envFilePath
$healthUrl = "http://127.0.0.1:$hostPort/health"

Write-Log "Starting automation-core startup sequence for $resolvedProjectRoot"

$dockerReady = $false
for ($elapsed = 0; $elapsed -lt $DockerWaitSeconds; $elapsed += 5) {
  & $docker info *> $null
  if ($LASTEXITCODE -eq 0) {
    $dockerReady = $true
    break
  }
  Start-Sleep -Seconds 5
}

if (-not $dockerReady) {
  Write-Log "Docker did not become ready within $DockerWaitSeconds seconds."
  exit 1
}

Write-Log "Docker is ready. Ensuring automation-core container is running."
$composeFilePath = Join-Path $resolvedProjectRoot "compose.yaml"
$stdoutPath = Join-Path $logDir "compose.stdout.log"
$stderrPath = Join-Path $logDir "compose.stderr.log"
Remove-Item $stdoutPath, $stderrPath -ErrorAction SilentlyContinue
$composeProcess = Start-Process -FilePath $docker `
  -ArgumentList @("compose", "-f", $composeFilePath, "up", "-d") `
  -WorkingDirectory $resolvedProjectRoot `
  -NoNewWindow `
  -Wait `
  -PassThru `
  -RedirectStandardOutput $stdoutPath `
  -RedirectStandardError $stderrPath
$composeOutput = @()
if (Test-Path $stdoutPath) {
  $composeOutput += Get-Content -LiteralPath $stdoutPath
}
if (Test-Path $stderrPath) {
  $composeOutput += Get-Content -LiteralPath $stderrPath
}
$composeExitCode = $composeProcess.ExitCode
$composeOutput | ForEach-Object { Write-Log "$_" }

if ($composeExitCode -ne 0) {
  Write-Log "docker compose up -d failed with exit code $composeExitCode."
  exit $composeExitCode
}

for ($elapsed = 0; $elapsed -lt $HealthWaitSeconds; $elapsed += 5) {
  try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
    if ($health.status -eq "ok") {
      Write-Log "automation-core is healthy at $healthUrl"
      exit 0
    }
  } catch {
    Write-Log "Waiting for automation-core health endpoint at $healthUrl"
  }

  Start-Sleep -Seconds 5
}

Write-Log "automation-core did not become healthy within $HealthWaitSeconds seconds."
exit 1
