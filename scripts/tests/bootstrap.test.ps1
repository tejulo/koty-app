$ErrorActionPreference = 'Stop'

$repositoryRoot = Resolve-Path (Join-Path $PSScriptRoot '../..')
$bootstrapPath = Join-Path $repositoryRoot 'scripts/bootstrap.ps1'
$doctorPath = Join-Path $repositoryRoot 'scripts/doctor.ps1'

function Assert-Contains {
    param(
        [string]$Content,
        [string]$Expected,
        [string]$Message
    )

    if (-not $Content.Contains($Expected)) {
        throw "FAIL: $Message"
    }
}

if (-not (Test-Path -LiteralPath $bootstrapPath)) {
    throw 'FAIL: scripts/bootstrap.ps1 is missing'
}

if (-not (Test-Path -LiteralPath $doctorPath)) {
    throw 'FAIL: scripts/doctor.ps1 is missing'
}

$bootstrap = Get-Content -LiteralPath $bootstrapPath -Raw
$doctor = Get-Content -LiteralPath $doctorPath -Raw

Assert-Contains $bootstrap 'install --id jdx.mise --exact' 'bootstrap does not install mise with winget'
Assert-Contains $bootstrap '[string]$MisePath' 'bootstrap cannot receive an explicitly resolved mise path'
Assert-Contains $bootstrap '$misePath install' 'bootstrap does not install the configured tools'
Assert-Contains $bootstrap 'pnpm install --frozen-lockfile' 'bootstrap does not sync Node dependencies reproducibly'
Assert-Contains $bootstrap 'uv sync --project crewai --frozen' 'bootstrap does not sync Python dependencies reproducibly'
Assert-Contains $bootstrap 'doctor.ps1' 'bootstrap does not invoke the PowerShell doctor'
Assert-Contains $bootstrap '$doctorPath -NoExit -MisePath $misePath' 'bootstrap does not pass the resolved mise path to doctor'
Assert-Contains $bootstrap 'mise activate pwsh' 'bootstrap does not document PowerShell activation'
Assert-Contains $doctor '[string]$MisePath' 'doctor cannot receive the resolved mise path'
Assert-Contains $doctor 'pnpm install --frozen-lockfile --lockfile-only' 'doctor does not validate the pnpm lockfile'
Assert-Contains $doctor 'uv lock --project crewai --check' 'doctor does not validate the uv lockfile'
Assert-Contains $doctor "import crew; print('crew import ok')" 'doctor does not validate the CrewAI import'

function Test-BootstrapUsesProvidedMise {
    $fixture = Join-Path ([System.IO.Path]::GetTempPath()) ("koty-bootstrap-" + [Guid]::NewGuid())
    $originalLocation = Get-Location

    try {
        New-Item -ItemType Directory -Path (Join-Path $fixture 'scripts') -Force | Out-Null
        New-Item -ItemType Directory -Path (Join-Path $fixture 'crewai') -Force | Out-Null
        Copy-Item -LiteralPath $bootstrapPath -Destination (Join-Path $fixture 'scripts/bootstrap.ps1')
        Copy-Item -LiteralPath $doctorPath -Destination (Join-Path $fixture 'scripts/doctor.ps1')
        Set-Content -LiteralPath (Join-Path $fixture 'crewai/.env.example') -Value 'LINEAR_API_KEY='
        Set-Content -LiteralPath (Join-Path $fixture 'crewai/.env') -Value 'KEEP=secret-value'

        $miseLog = Join-Path $fixture 'mise.log'
        $fakeMisePath = Join-Path $fixture 'mise.ps1'
        Set-Content -LiteralPath $fakeMisePath -Value @'
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

Add-Content -LiteralPath $env:BOOTSTRAP_TEST_MISE_LOG -Value ($Arguments -join ' ')
$command = $Arguments -join ' '
if ($command -eq 'exec -- node --version') { Write-Output 'v20.20.2' }
if ($command -eq 'exec -- pnpm --version') { Write-Output '11.3.0' }
if ($command -eq 'exec -- uv --version') { Write-Output 'uv 0.11.16' }
if ($command -eq 'exec -- python --version') { Write-Output 'Python 3.12.13' }
$global:LASTEXITCODE = 0
'@

        $env:BOOTSTRAP_TEST_MISE_LOG = $miseLog
        $output = & (Join-Path $fixture 'scripts/bootstrap.ps1') -MisePath $fakeMisePath 6>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "FAIL: bootstrap exited with code $LASTEXITCODE"
        }

        $commands = Get-Content -LiteralPath $miseLog -Raw
        Assert-Contains $commands 'install' 'bootstrap did not install configured tools'
        Assert-Contains $commands 'exec -- pnpm install --frozen-lockfile' 'bootstrap did not sync pnpm dependencies'
        Assert-Contains $commands 'exec -- uv sync --project crewai --frozen' 'bootstrap did not sync uv dependencies'
        Assert-Contains $commands 'exec -- node --version' 'doctor did not use the injected mise path'
        Assert-Contains (Get-Content -LiteralPath (Join-Path $fixture 'crewai/.env') -Raw) 'KEEP=secret-value' 'bootstrap overwrote an existing environment file'
        if ($output.Contains('secret-value')) {
            throw 'FAIL: bootstrap output revealed an environment value'
        }
    } finally {
        Set-Location -LiteralPath $originalLocation
        Remove-Item -LiteralPath $fixture -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item Env:BOOTSTRAP_TEST_MISE_LOG -ErrorAction SilentlyContinue
    }
}

Test-BootstrapUsesProvidedMise

Write-Output 'PASS: PowerShell bootstrap behavior'
