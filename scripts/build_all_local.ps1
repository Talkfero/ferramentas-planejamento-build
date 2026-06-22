<#
.SYNOPSIS
  Build all LOCAL (Windows) — espelho do workflow .github/workflows/build-installer.yml,
  rodando 100% offline (sem GitHub Actions, sem BUILD_REPO_READ_TOKEN).

.DESCRIPTION
  Replica, na sua maquina, exatamente os passos do CI:
    1. Monta apps/ a partir dos repos irmaos locais (prepare_apps_local.ps1).
    2. Valida o layout (scripts/validate_layout.py).
    3. Instala deps + roda o PyInstaller (build_all_shared.bat) num venv isolado.
    4. Copia os configs .NET (scripts/finalize_bundle.ps1).
    5. Valida o runtime pywebview + self-test do Coplan (validate_runtime_bundle.ps1).
    6. (Opcional) compila o instalador Inno Setup, se o ISCC estiver instalado.

  Capex foi fundido no Coplan (capex_engine): nao existe mais Ambiente Capex.exe;
  o Coplan Web ja o embarca.

.PARAMETER Apps
  "all" (default) ou um subconjunto separado por virgula (ex.: "coplan_web,cadastro").

.PARAMETER SkipInstaller
  Nao tenta compilar o .iss (gera so o bundle dist/FerramentasCompartilhadas).

.PARAMETER RecreateVenv
  Recria o venv .build_venv do zero.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\build_all_local.ps1
#>
param(
  [string]$Apps = "all",
  [switch]$SkipInstaller,
  [switch]$RecreateVenv
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..").Path
$VenvDir = Join-Path $env:TEMP "fplan_build_venv"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"

function Write-Step($msg) {
  Write-Host ""
  Write-Host "==================================================================" -ForegroundColor Cyan
  Write-Host "  $msg" -ForegroundColor Cyan
  Write-Host "==================================================================" -ForegroundColor Cyan
}

Push-Location $Root
try {
  Write-Step "0/6  Ambiente"
  Write-Host "Repo build : $Root"
  Write-Host "Apps       : $Apps"
  & python --version

  # --- venv isolado ---------------------------------------------------------
  if ($RecreateVenv -and (Test-Path $VenvDir)) {
    Write-Host "Removendo venv antigo: $VenvDir"
    Remove-Item -Recurse -Force $VenvDir
  }
  if (-not (Test-Path $VenvPy)) {
    Write-Step "Criando venv isolado em .build_venv"
    & python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o venv." }
  }
  Write-Host "Python do build: $VenvPy"
  & $VenvPy -m pip install --upgrade pip wheel setuptools
  if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar pip no venv." }

  # Coloca o venv na frente do PATH para que o build_all_shared.bat (que chama
  # `python` puro) use o interpretador isolado, nao o global.
  $env:PATH = (Join-Path $VenvDir "Scripts") + ";" + $env:PATH
  $env:VIRTUAL_ENV = $VenvDir
  $env:PYTHONIOENCODING = "utf-8"

  # Trava de versoes (supply-chain): se existir requirements.lock.txt, usa como
  # constraint em TODOS os pip install (apps usam >= nos requirements; o lock
  # fixa a versao exata validada). Regenerar: pip freeze > requirements.lock.txt.
  $lock = Join-Path $Root "requirements.lock.txt"
  if (Test-Path $lock) {
    # pip nao suporta PIP_CONSTRAINT com espacos no caminho; copia p/ TEMP sem espacos.
    $lockTemp = Join-Path $env:TEMP "fplan_requirements.lock.txt"
    Copy-Item $lock $lockTemp -Force
    $env:PIP_CONSTRAINT = $lockTemp
    Write-Host "PIP_CONSTRAINT = $lockTemp (copia sem espacos)"
  }

  # --- 1) montar apps/ a partir dos repos locais ----------------------------
  Write-Step "1/6  Montando apps/ a partir dos repos locais (espelho, sem token)"
  & "$PSScriptRoot\prepare_apps_local.ps1" -Force

  # --- 2) validar layout ----------------------------------------------------
  Write-Step "2/6  Validando layout de apps/"
  & $VenvPy "$PSScriptRoot\validate_layout.py" --apps $Apps
  if ($LASTEXITCODE -ne 0) { throw "Layout incompleto (validate_layout)." }

  # --- 3) deps + PyInstaller ------------------------------------------------
  Write-Step "3/6  Instalando deps + rodando PyInstaller (build_all_shared.bat $Apps)"
  $env:APPS_TO_BUILD = $Apps
  & "$Root\build_all_shared.bat" $Apps
  if ($LASTEXITCODE -ne 0) { throw "build_all_shared.bat falhou (exit=$LASTEXITCODE)." }

  $distExe = Join-Path $Root "dist\FerramentasCompartilhadas"
  if (-not (Test-Path (Join-Path $distExe "_internal\base_library.zip"))) {
    throw "Bundle nao gerado: faltou dist\FerramentasCompartilhadas\_internal."
  }

  # --- 4) finalize (configs .NET) -------------------------------------------
  Write-Step "4/6  Copiando configs .NET (finalize_bundle.ps1)"
  & "$PSScriptRoot\finalize_bundle.ps1"

  # --- 5) validar runtime pywebview + self-test do Coplan -------------------
  Write-Step "5/6  Validando runtime pywebview + self-test do Coplan"
  & "$PSScriptRoot\validate_runtime_bundle.ps1" -Apps $Apps

  # --- 6) instalador Inno Setup (opcional) ----------------------------------
  Write-Step "6/6  Instalador Inno Setup"
  if ($SkipInstaller) {
    Write-Host "[skip] -SkipInstaller setado; bundle pronto em dist\FerramentasCompartilhadas."
  } else {
    $iscc = $null
    foreach ($c in @(
        (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source,
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"))) {
      if ($c -and (Test-Path $c)) { $iscc = $c; break }
    }
    if (-not $iscc) {
      Write-Warning "ISCC.exe (Inno Setup) nao encontrado. Bundle pronto, mas o instalador .exe NAO foi gerado."
      Write-Host    "  Instale com:  winget install -e --id JRSoftware.InnoSetup"
      Write-Host    "  Depois rode:  ISCC Setup_turbinado.iss   (na raiz do repo)"
    } else {
      Write-Host "Usando ISCC: $iscc"
      $issArgs = @()
      $appsNorm = $Apps.Trim().ToLowerInvariant()
      if ($appsNorm -ne "all" -and -not ($appsNorm.Contains(",") -or $appsNorm.Contains(";"))) {
        $issArgs += "/DAPP_ONLY=$appsNorm"
      }
      $issArgs += "$Root\Setup_turbinado.iss"
      & $iscc @issArgs
      if ($LASTEXITCODE -ne 0) { throw "ISCC falhou (exit=$LASTEXITCODE)." }
      $out = Get-ChildItem (Join-Path $Root "Output\*.exe") -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($out) { Write-Host "Instalador gerado: $($out.FullName)" -ForegroundColor Green }
    }
  }

  Write-Step "BUILD ALL CONCLUIDO"
  Write-Host "Bundle: $distExe" -ForegroundColor Green
  Get-ChildItem $distExe -Filter *.exe | ForEach-Object { Write-Host ("  - " + $_.Name) }
}
finally {
  Pop-Location
}

