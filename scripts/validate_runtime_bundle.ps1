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
    # elexplan entrou na lista em 31/07/2026: a suite passou a empacotar a UI
    # WEB (pywebview) dele, entao ele tambem depende de WebView2/pythonnet.
    $tokens = @("elexplan", "coplan_web", "cadastro")
} else {
    $tokens = $Apps.ToLowerInvariant().Replace(";", ",").Split(",") |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
}

$aliases = @{
    "coplan" = "coplan_web"
    # Capex fundido no Coplan (capex_engine): "capex" -> coplan_web.
    "capex"  = "coplan_web"
}
$tokens = $tokens | ForEach-Object {
    if ($aliases.ContainsKey($_)) { $aliases[$_] } else { $_ }
}

$webApps = @{
    "elexplan" = "Elexplan.exe"
    "coplan_web" = "Coplan Web.exe"
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

# ---------------------------------------------------------------------------
# Smoke-test de import do Coplan (so DLLs nao basta).
# Roda "Coplan Web.exe" em modo self-test (COPLAN_SELFTEST=1, sem janela): o
# launcher importa a cadeia de managers e confirma que o DatabaseManager
# instancia. Pega "DatabaseManager indisponivel" -- um modulo Python que ficou
# de fora do bundle do PyInstaller -- ANTES de publicar o instalador. As
# checagens de DLL acima validam o runtime .NET/WebView2, nao o grafo de
# modulos Python do app.
# ---------------------------------------------------------------------------
if ($selectedWebApps -contains "coplan_web") {
    $coplanExe = Join-Path $Dist "Coplan Web.exe"
    if (-not (Test-Path $coplanExe)) {
        throw "Executavel ausente para self-test do Coplan: Coplan Web.exe"
    }
    $log = Join-Path ([System.IO.Path]::GetTempPath()) ("coplan_selftest_{0}.log" -f ([guid]::NewGuid().ToString("N")))
    if (Test-Path $log) { Remove-Item $log -Force }

    $env:COPLAN_SELFTEST = "1"
    $env:COPLAN_SELFTEST_LOG = $log
    $code = $null
    try {
        $proc = Start-Process -FilePath $coplanExe -PassThru -WindowStyle Hidden
        $proc | Wait-Process -Timeout 120 -ErrorAction SilentlyContinue
        if (-not $proc.HasExited) {
            try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
            throw "[validate_runtime_bundle] Coplan self-test excedeu 120s (travou ao iniciar?)."
        }
        $code = $proc.ExitCode
    } finally {
        Remove-Item Env:\COPLAN_SELFTEST -ErrorAction SilentlyContinue
        Remove-Item Env:\COPLAN_SELFTEST_LOG -ErrorAction SilentlyContinue
    }

    # O log e' a fonte de verdade do resultado (o .exe e' windowed: o
    # ExitCode do Start-Process as vezes vem nulo; o marcador "OK:" no log
    # e' escrito sempre pelo launcher).
    if (-not (Test-Path $log)) {
        throw "[validate_runtime_bundle] Coplan self-test nao gerou log (exe nao rodou? exit=$code)."
    }
    $detail = (Get-Content -Raw -Encoding UTF8 $log).Trim()
    Remove-Item $log -Force -ErrorAction SilentlyContinue
    if ($detail -notmatch "OK:") {
        throw "[validate_runtime_bundle] Coplan self-test FALHOU (exit=$code). $detail"
    }
    Write-Host "[validate_runtime_bundle] Coplan self-test OK (exit=$code). $detail"
}

# O PIM importa Playwright somente quando o navegador e' solicitado. Testar a
# abertura normal do Elexplan nao alcanca esse caminho; o modo self-test inicia
# e encerra o driver empacotado sem abrir browser nem janela.
if ($selectedWebApps -contains "elexplan") {
    $elexplanExe = Join-Path $Dist "Elexplan.exe"
    $log = Join-Path ([System.IO.Path]::GetTempPath()) ("elexplan_selftest_{0}.log" -f ([guid]::NewGuid().ToString("N")))
    if (Test-Path $log) { Remove-Item $log -Force }

    $env:ELEXPLAN_SELFTEST = "1"
    $env:ELEXPLAN_SELFTEST_LOG = $log
    $code = $null
    try {
        $proc = Start-Process -FilePath $elexplanExe -PassThru -WindowStyle Hidden
        $proc | Wait-Process -Timeout 60 -ErrorAction SilentlyContinue
        if (-not $proc.HasExited) {
            try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
            throw "[validate_runtime_bundle] Elexplan self-test excedeu 60s."
        }
        $code = $proc.ExitCode
    } finally {
        Remove-Item Env:\ELEXPLAN_SELFTEST -ErrorAction SilentlyContinue
        Remove-Item Env:\ELEXPLAN_SELFTEST_LOG -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path $log)) {
        throw "[validate_runtime_bundle] Elexplan self-test nao gerou log (exit=$code)."
    }
    $detail = (Get-Content -Raw -Encoding UTF8 $log).Trim()
    Remove-Item $log -Force -ErrorAction SilentlyContinue
    if ($detail -notmatch "^OK:") {
        throw "[validate_runtime_bundle] Elexplan self-test FALHOU (exit=$code). $detail"
    }
    Write-Host "[validate_runtime_bundle] Elexplan self-test OK (exit=$code). $detail"
}

Write-Host "[validate_runtime_bundle] runtime pywebview OK para: $($selectedWebApps -join ', ')"
