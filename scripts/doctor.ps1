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

function Update-ProcessPath {
    $pathEntries = @(
        $env:PATH
        [Environment]::GetEnvironmentVariable('Path', 'User')
        [Environment]::GetEnvironmentVariable('Path', 'Machine')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    $env:PATH = $pathEntries -join ';'
}

function Invoke-MiseCapture {
    param([string[]]$Arguments)

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $script:misePath @Arguments 2>$null
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    [pscustomobject]@{
        ExitCode = $exitCode
        Output = ($output -join "`n").Trim()
    }
}

function Test-Version {
    param(
        [string]$Tool,
        [string]$Expected
    )

    $result = Invoke-MiseCapture @('exec', '--', $Tool, '--version')
    if ($result.ExitCode -ne 0) {
        Report-Error "$Tool version check failed"
        return
    }

    $actual = $result.Output
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

    $result = Invoke-MiseCapture $Arguments
    if ($result.ExitCode -ne 0) {
        Report-Error "$Message failed"
    } else {
        Write-Host "OK: $Message"
    }
}

if (-not [string]::IsNullOrWhiteSpace($MisePath)) {
    $script:misePath = $MisePath
} else {
    Update-ProcessPath
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
        $parser = "import sys; from dotenv import dotenv_values; required = ('LINEAR_API_KEY', 'OPENCODE_API_KEY', 'ZEN_BASE_URL', 'ZEN_ANALYST_MODEL', 'ZEN_ARCHITECT_MODEL', 'ZEN_CODER_MODEL', 'ZEN_REVIEWER_MODEL'); values = dotenv_values(sys.argv[1]); [print(key) for key in required if not values.get(key)]"
        $result = Invoke-MiseCapture @('exec', '--', 'uv', 'run', '--project', 'crewai', '--no-sync', 'python', '-c', $parser, $environmentPath)
        if ($result.ExitCode -ne 0) {
            Report-Error 'environment file validation failed'
        } else {
            foreach ($key in $result.Output -split "`r?`n") {
                if (-not [string]::IsNullOrWhiteSpace($key)) {
                    Report-Error "empty environment variable: $key"
                }
            }
        }
    }

    $pnpmLockfileCommand = 'pnpm install --frozen-lockfile --lockfile-only'.Split(' ')
    $uvLockCommand = 'uv lock --project crewai --check'.Split(' ')
    Test-Command 'pnpm frozen lockfile check' (@('exec', '--') + $pnpmLockfileCommand)
    Test-Command 'uv lock check' (@('exec', '--') + $uvLockCommand)

    $previousTelemetry = $env:OPENSPEC_TELEMETRY
    $env:OPENSPEC_TELEMETRY = '0'
    try {
        Test-Command 'OpenSpec strict validation' @('exec', '--', 'pnpm', 'exec', 'openspec', 'validate', '--all', '--strict')
    } finally {
        $env:OPENSPEC_TELEMETRY = $previousTelemetry
    }

    Test-Command 'crew import' @('exec', '--', 'uv', 'run', '--project', 'crewai', '--no-sync', 'python', '-c', "import crew; print('crew import ok')")
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
