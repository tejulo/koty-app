[CmdletBinding()]
param(
    [switch]$NoExit,
    [string]$MisePath
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$script:failed = $false

function Report-Error {
    param([string]$Message)

    Write-Host "ERROR: $Message"
    $script:failed = $true
}

function Test-Version {
    param(
        [string]$Tool,
        [string]$Expected
    )

    $output = & $script:misePath exec -- $Tool --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Report-Error "$Tool version check failed"
        return
    }

    $actual = (($output -join "`n").Trim())
    switch ($Tool) {
        'node' { $actual = $actual.TrimStart('v') }
        'python' { $actual = $actual -replace '^Python\s+', '' }
        'uv' { $actual = ($actual -replace '^uv\s+', '').Split([char[]]' ')[0] }
    }

    if ($actual -ne $Expected) {
        Report-Error "$Tool version: expected $Expected, got $actual"
    } else {
        Write-Host "OK: $Tool version $Expected"
    }
}

function Test-Command {
    param(
        [string]$Message,
        [string[]]$Arguments
    )

    & $script:misePath @Arguments *> $null
    if ($LASTEXITCODE -ne 0) {
        Report-Error "$Message failed"
    } else {
        Write-Host "OK: $Message"
    }
}

if (-not [string]::IsNullOrWhiteSpace($MisePath)) {
    $script:misePath = $MisePath
} else {
    $miseCommand = Get-Command mise -ErrorAction SilentlyContinue
    if ($null -ne $miseCommand) {
        $script:misePath = $miseCommand.Source
    } else {
        $wingetLink = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\mise.exe'
        if (Test-Path -LiteralPath $wingetLink) {
            $script:misePath = $wingetLink
        } else {
            Report-Error 'mise is not available'
        }
    }
}

Set-Location -LiteralPath $repositoryRoot
$environmentPath = Join-Path $repositoryRoot 'crewai/.env'

if (-not $script:failed) {
    Test-Version 'node' '20.20.2'
    Test-Version 'pnpm' '11.3.0'
    Test-Version 'uv' '0.11.16'
    Test-Version 'python' '3.12.13'

    if (-not (Test-Path -LiteralPath $environmentPath)) {
        Report-Error 'missing environment file: crewai/.env'
    } else {
        $parser = @'
import sys
from dotenv import dotenv_values

required = (
    "LINEAR_API_KEY",
    "OPENCODE_API_KEY",
    "ZEN_BASE_URL",
    "ZEN_ANALYST_MODEL",
    "ZEN_ARCHITECT_MODEL",
    "ZEN_CODER_MODEL",
    "ZEN_REVIEWER_MODEL",
)
values = dotenv_values(sys.argv[1])
for key in required:
    if not values.get(key):
        print(key)
'@
        $missing = @(& $script:misePath exec -- uv run --project crewai --no-sync python -c $parser $environmentPath 2>$null)
        if ($LASTEXITCODE -ne 0) {
            Report-Error 'environment file validation failed'
        } else {
            foreach ($key in $missing) {
                if (-not [string]::IsNullOrWhiteSpace($key)) {
                    Report-Error "empty environment variable: $key"
                }
            }
        }
    }

    & $script:misePath exec -- pnpm install --frozen-lockfile --lockfile-only *> $null
    if ($LASTEXITCODE -ne 0) {
        Report-Error 'pnpm frozen lockfile check failed'
    } else {
        Write-Host 'OK: pnpm frozen lockfile check'
    }

    & $script:misePath exec -- uv lock --project crewai --check *> $null
    if ($LASTEXITCODE -ne 0) {
        Report-Error 'uv lock check failed'
    } else {
        Write-Host 'OK: uv lock check'
    }

    $previousTelemetry = $env:OPENSPEC_TELEMETRY
    $env:OPENSPEC_TELEMETRY = '0'
    & $script:misePath exec -- pnpm exec openspec validate --all --strict *> $null
    $openspecExitCode = $LASTEXITCODE
    $env:OPENSPEC_TELEMETRY = $previousTelemetry
    if ($openspecExitCode -ne 0) {
        Report-Error 'OpenSpec strict validation failed'
    } else {
        Write-Host 'OK: OpenSpec strict validation'
    }

    & $script:misePath exec -- uv run --project crewai --no-sync python -c "import crew; print('crew import ok')" *> $null
    if ($LASTEXITCODE -ne 0) {
        Report-Error 'crew import failed'
    } else {
        Write-Host 'OK: crew import'
    }
}

if ($script:failed) {
    if ($NoExit) {
        return $false
    }
    exit 1
}

Write-Host 'OK: environment checks passed'
if ($NoExit) {
    return $true
}
