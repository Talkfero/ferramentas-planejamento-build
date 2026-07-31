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

# ---------------------------------------------------------------------------
# Minor version do Python do build. TEM de ser a mesma do CI
# (.github/workflows/build-installer.yml: python-version "3.12") e a do bundle
# publicado.
#
# Nao e' preciosismo: as extensoes C (.pyd de pandas/numpy/...) e a
# pythonXYZ.dll entram no _internal com a ABI do interpretador que compilou.
# Como o bundle e' COMPARTILHADO, buildar um app numa minor diferente e junta-lo
# ao resto -- por overlay ou instalando por cima -- deixa o .exe de um app
# carregando .pyd de outra versao, e ele quebra no import.
#
# Cuidado: em maquina com varios Pythons, `python` no PATH pode NAO ser o 3.12
# (e' o caso da maquina do dev em 31/07/2026, onde o default e' 3.14). Por isso
# resolvemos pelo py launcher em vez de confiar no PATH.
# ---------------------------------------------------------------------------
$PyMinor = "3.12"

function Write-Step($msg) {
  Write-Host ""
  Write-Host "==================================================================" -ForegroundColor Cyan
  Write-Host "  $msg" -ForegroundColor Cyan
  Write-Host "==================================================================" -ForegroundColor Cyan
}

# PS 5.1: com $ErrorActionPreference = "Stop", QUALQUER linha em stderr de um
# executavel nativo vira NativeCommandError TERMINANTE -- inclusive quando
# redirecionada para $null. Sondar versao e' justamente o caso em que o
# processo FALHA de proposito: venv corrompido (Scripts\python.exe sem
# pyvenv.cfg, deixado por uma rodada anterior) responde "No pyvenv.cfg file",
# e um `py -3.XX` inexistente tambem escreve em stderr. Sem baixar o EAP aqui,
# a deteccao derruba o script que ela deveria salvar.
function Invoke-PyProbe([string]$Exe, [string[]]$PyArgs) {
  $old = $ErrorActionPreference
  $ErrorActionPreference = "SilentlyContinue"
  try {
    $out = & $Exe @PyArgs 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $txt = ("$out").Trim()
    if (-not $txt) { return $null }
    return $txt
  } catch {
    return $null
  } finally {
    $ErrorActionPreference = $old
  }
}

function Get-PythonMinor([string]$Exe) {
  if (-not $Exe -or -not (Test-Path $Exe)) { return $null }
  return Invoke-PyProbe $Exe @("-c", "import sys; print('%d.%d' % sys.version_info[:2])")
}

function Resolve-BuildPython([string]$Minor) {
  # 1) py launcher pedindo a minor exata (caminho confiavel com varios Pythons).
  if (Get-Command py -ErrorAction SilentlyContinue) {
    $exe = Invoke-PyProbe "py" @("-$Minor", "-c", "import sys; print(sys.executable)")
    if ($exe -and (Test-Path $exe)) { return $exe }
  }
  # 2) o `python` do PATH, mas SO' se ja for a minor certa.
  $p = Get-Command python -ErrorAction SilentlyContinue
  if ($p -and (Get-PythonMinor $p.Source) -eq $Minor) { return $p.Source }
  return $null
}

Push-Location $Root
try {
  Write-Step "0/6  Ambiente"
  Write-Host "Repo build : $Root"
  Write-Host "Apps       : $Apps"

  $BuildPython = Resolve-BuildPython $PyMinor
  if (-not $BuildPython) {
    throw ("Python $PyMinor nao encontrado. O CI e o bundle publicado usam " +
           "$PyMinor; compilar noutra minor gera _internal com ABI incompativel " +
           "com os demais apps da suite. Instale com:  " +
           "winget install -e --id Python.Python.$PyMinor")
  }
  Write-Host "Python base: $BuildPython (minor $PyMinor)"

  # --- venv isolado ---------------------------------------------------------
  if ($RecreateVenv -and (Test-Path $VenvDir)) {
    Write-Host "Removendo venv antigo: $VenvDir"
    Remove-Item -Recurse -Force $VenvDir
  }
  # venv que sobrou de OUTRA minor -- ou corrompido, sem pyvenv.cfg -- nao
  # serve. Recria, em vez de gerar um bundle silenciosamente incompativel ou
  # morrer mais adiante num erro sem relacao aparente.
  if (Test-Path $VenvPy) {
    $venvMinor = Get-PythonMinor $VenvPy
    if ($venvMinor -ne $PyMinor) {
      $comoEsta = if ($venvMinor) { "e' $venvMinor" } else { "esta quebrado" }
      Write-Host "venv existente $comoEsta (esperado $PyMinor) -- recriando."
      Remove-Item -Recurse -Force $VenvDir
    }
  }
  if (-not (Test-Path $VenvPy)) {
    Write-Step "Criando venv isolado ($PyMinor) em $VenvDir"
    & $BuildPython -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o venv." }
  }
  Write-Host "Python do build: $VenvPy ($(Get-PythonMinor $VenvPy))"
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

