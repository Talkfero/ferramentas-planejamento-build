$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Dist = Join-Path $Root "dist\FerramentasCompartilhadas"
$ConfigDir = Join-Path $Root "app_configs"

if (-not (Test-Path $Dist)) {
    throw "Bundle ausente: $Dist"
}

if (Test-Path $ConfigDir) {
    Get-ChildItem $ConfigDir -Filter "*.exe.config" | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $Dist $_.Name) -Force
        Write-Host "[finalize_bundle] copiado: $($_.Name)"
    }
}

# Elexplan entrou aqui em 31/07/2026, quando a suite passou a empacotar a UI
# WEB (pywebview) em vez do Qt legado -- ver ELEXPLAN_ENTRY em multi_apps.spec.
$expected = @(
    "Elexplan.exe.config",
    "Coplan Web.exe.config",
    "Sistema de Cadastro.exe.config"
)

foreach ($name in $expected) {
    $path = Join-Path $Dist $name
    if (-not (Test-Path $path)) {
        throw "Config runtime ausente no bundle: $name"
    }
}
