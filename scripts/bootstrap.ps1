[CmdletBinding()]
param(
    [string]$MisePath
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$miseCommand = $null

function Update-ProcessPath {
    $pathEntries = @(
        $env:PATH
        [Environment]::GetEnvironmentVariable('Path', 'User')
        [Environment]::GetEnvironmentVariable('Path', 'Machine')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    $env:PATH = $pathEntries -join ';'
}

if ([string]::IsNullOrWhiteSpace($MisePath)) {
    Update-ProcessPath
    $miseCommand = Get-Command mise -ErrorAction SilentlyContinue

    if ($null -eq $miseCommand) {
        $wingetCommand = Get-Command winget -ErrorAction SilentlyContinue
        if ($null -eq $wingetCommand) {
            throw 'mise is not available and winget is required to install it. Install mise manually and run this script again.'
        }

        & $wingetCommand.Source install --id jdx.mise --exact --accept-package-agreements --accept-source-agreements
        $wingetStatus = $LASTEXITCODE
        Update-ProcessPath
        $miseCommand = Get-Command mise -ErrorAction SilentlyContinue
        if ($null -eq $miseCommand -and $wingetStatus -ne 0) {
            throw "winget could not install mise (exit code $wingetStatus)."
        }

        if ($null -eq $miseCommand) {
            $wingetLink = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\mise.exe'
            if (Test-Path -LiteralPath $wingetLink) {
                $misePath = $wingetLink
            } else {
                throw 'mise was installed, but is not available in this PowerShell session. Restart PowerShell and run this script again.'
            }
        }
    }

    if ($null -ne $miseCommand) {
        $misePath = $miseCommand.Source
    }
}

Set-Location -LiteralPath $repositoryRoot

# Equivalent native call: & $misePath install
& $misePath @('install')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$pnpmInstallCommand = 'pnpm install --frozen-lockfile'.Split(' ')
& $misePath (@('exec', '--') + $pnpmInstallCommand)
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$uvSyncCommand = 'uv sync --project crewai --frozen'.Split(' ')
& $misePath (@('exec', '--') + $uvSyncCommand)
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$environmentPath = Join-Path $repositoryRoot 'crewai/.env'
if (-not (Test-Path -LiteralPath $environmentPath)) {
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'crewai/.env.example') -Destination $environmentPath
}

$doctorPath = Join-Path $PSScriptRoot 'doctor.ps1'
$doctorPassed = & $doctorPath -NoExit -MisePath $misePath
if (-not $doctorPassed) {
    Write-Error 'Corrige los errores reportados por doctor y ejecuta nuevamente: .\scripts\doctor.ps1'
    exit 1
}

$profileLine = '(& mise activate pwsh) | Out-String | Invoke-Expression'
Write-Host 'Entorno preparado.'
Write-Host 'El bootstrap no puede modificar la sesion padre.'
Write-Host 'Para habilitar mise en PowerShell, ejecuta:'
Write-Host '  if (-not (Test-Path -LiteralPath $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }'
Write-Host "  if (-not (Select-String -LiteralPath `$PROFILE -SimpleMatch '$profileLine' -Quiet)) { Add-Content -LiteralPath `$PROFILE -Value '$profileLine' }"
Write-Host '  . $PROFILE'
Write-Host 'Luego ejecuta:'
Write-Host '  pnpm verify'
Write-Host '  Set-Location crewai'
Write-Host '  uv run run_crew DEV-5'
Write-Host 'Alternativa sin modificar el perfil:'
Write-Host "  & '$misePath' exec -- pnpm verify"
Write-Host "  & '$misePath' exec -- uv run --project crewai run_crew DEV-5"
