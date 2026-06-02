param(
  [string]$AppsRoot = (Join-Path (Resolve-Path "$PSScriptRoot\..") "apps"),
  [switch]$Force
)

$ErrorActionPreference = "Stop"

$repos = @(
  @{ Target = "launcher";              Url = "https://github.com/Talkfero/Ferramenta_plan.git" },
  @{ Target = "elexplan";              Url = "https://github.com/Talkfero/elexplan.git" },
  @{ Target = "diagnostico";           Url = "https://github.com/Talkfero/diagnostico_atual.git" },
  @{ Target = "coplan";                Url = "https://github.com/Talkfero/coplanweb.git" },
  @{ Target = "capex";                 Url = "https://github.com/Talkfero/capex.git" },
  @{ Target = "status_medicao";        Url = "https://github.com/Talkfero/status_medicao.git" },
  @{ Target = "cadastro_viabilidades"; Url = "https://github.com/Talkfero/sistemadecadastro.git" }
)

New-Item -ItemType Directory -Force -Path $AppsRoot | Out-Null

function Apply-PatchIfNeeded([string]$Target, [string]$PatchFile) {
  if (-not (Test-Path $Target)) {
    throw "Diretorio alvo do patch nao encontrado: $Target"
  }
  if (-not (Test-Path $PatchFile)) {
    throw "Patch nao encontrado: $PatchFile"
  }

  git -C $Target apply --check $PatchFile 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "[prepare_apps] aplicando patch: $PatchFile"
    git -C $Target apply $PatchFile
    if ($LASTEXITCODE -ne 0) {
      throw "Falha ao aplicar patch: $PatchFile"
    }
    return
  }

  git -C $Target apply --reverse --check $PatchFile 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "[prepare_apps] patch ja aplicado: $PatchFile"
    return
  }

  throw "Patch incompativel com o codigo clonado: $PatchFile"
}

function Get-CloneUrl([string]$Url) {
  $token = $env:GH_PAT
  if (-not $token) { $token = $env:BUILD_REPO_READ_TOKEN }
  if (-not $token) { $token = $env:GH_TOKEN }
  if (-not $token) { return $Url }
  return ($Url -replace '^https://github.com/', "https://x-access-token:$token@github.com/")
}

foreach ($repo in $repos) {
  $target = Join-Path $AppsRoot $repo.Target
  if (Test-Path $target) {
    if ($Force) {
      Remove-Item -Recurse -Force $target
    } else {
      Write-Host "[prepare_apps] existe, mantendo: apps/$($repo.Target)"
      continue
    }
  }

  Write-Host "[prepare_apps] clone $($repo.Url) -> apps/$($repo.Target)"
  git clone --depth 1 (Get-CloneUrl $repo.Url) $target
}

$launcherPatch = Join-Path (Resolve-Path "$PSScriptRoot/..") "patches/launcher-instance-management.patch"
Apply-PatchIfNeeded (Join-Path $AppsRoot "launcher") $launcherPatch

Write-Host "[prepare_apps] pronto."
