param(
  [string]$Apps = "all"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Dist = Join-Path $Root "dist\FerramentasCompartilhadas"

if (-not (Test-Path $Dist)) {
    throw "Bundle ausente: $Dist"
}

$tokens = @()
if ([string]::IsNullOrWhiteSpace($Apps) -or $Apps.Trim().ToLowerInvariant() -eq "all") {
    $tokens = @("coplan_web", "capex", "cadastro")
} else {
    $tokens = $Apps.ToLowerInvariant().Replace(";", ",").Split(",") |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
}

$aliases = @{
    "coplan" = "coplan_web"
}
$tokens = $tokens | ForEach-Object {
    if ($aliases.ContainsKey($_)) { $aliases[$_] } else { $_ }
}

$webApps = @{
    "coplan_web" = "Coplan Web.exe"
    "capex" = "Ambiente Capex.exe"
    "cadastro" = "Sistema de Cadastro.exe"
}

$selectedWebApps = @()
foreach ($token in $tokens) {
    if ($webApps.ContainsKey($token)) {
        $selectedWebApps += $token
    }
}

if (-not $selectedWebApps) {
    Write-Host "[validate_runtime_bundle] nenhum app pywebview selecionado; pulando."
    exit 0
}

$sharedRequired = @(
    "_internal\pythonnet\runtime\Python.Runtime.dll",
    "_internal\clr_loader\ffi\dlls\amd64\ClrLoader.dll",
    "_internal\webview\lib\Microsoft.Web.WebView2.Core.dll",
    "_internal\webview\platforms\winforms.py"
)

foreach ($rel in $sharedRequired) {
    $path = Join-Path $Dist $rel
    if (-not (Test-Path $path)) {
        throw "Dependencia runtime ausente no bundle: $rel"
    }
}

$configNeedles = @(
    'useLegacyV2RuntimeActivationPolicy="true"',
    'loadFromRemoteSources enabled="true"',
    '_internal\pythonnet\runtime',
    '_internal\clr_loader\ffi\dlls\amd64'
)

foreach ($key in $selectedWebApps) {
    $exeName = $webApps[$key]
    $exePath = Join-Path $Dist $exeName
    $configPath = "$exePath.config"

    if (-not (Test-Path $exePath)) {
        throw "Executavel pywebview ausente: $exeName"
    }
    if (-not (Test-Path $configPath)) {
        throw "Config .NET ausente ao lado do executavel: $exeName.config"
    }

    $configText = Get-Content -Raw -Encoding UTF8 $configPath
    foreach ($needle in $configNeedles) {
        if ($configText -notlike "*$needle*") {
            throw "Config $exeName.config nao contem trecho obrigatorio: $needle"
        }
    }
}

Write-Host "[validate_runtime_bundle] runtime pywebview OK para: $($selectedWebApps -join ', ')"
