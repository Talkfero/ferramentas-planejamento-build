param(
  [string]$AppsRoot = (Join-Path (Resolve-Path "$PSScriptRoot\..") "apps"),
  [switch]$Force
)

$ErrorActionPreference = "Stop"

$repos = @(
  @{ Target = "launcher";              Url = "https://github.com/Talkfero/Ferramenta_plan.git" },
  @{ Target = "elexplan";              Url = "https://github.com/Talkfero/elexplan.git" },
  @{ Target = "diagnostico";           Url = "https://github.com/Talkfero/diagnostico_atual.git" },
  # Capex foi fundido dentro do Coplan (capex_engine vendorizado em coplanweb/);
  # nao ha mais repo/app/exe capex separado. Ver coplanweb/backend/domains/capex.py
  # (regra user 2026-06-18 "coplan vira a ferramenta unica").
  @{ Target = "coplan";                Url = "https://github.com/Talkfero/coplanweb.git" },
  # Status de Medicao foi fundido dentro do Elexplan (chaves + status PIM +
  # estatistica); nao ha mais app/exe/repo status_medicao separado. Ver
  # elexplan/codigo1_elexplan.py (regra user 2026-06-18).
  @{ Target = "cadastro_viabilidades"; Url = "https://github.com/Talkfero/sistemadecadastro.git" }
)

New-Item -ItemType Directory -Force -Path $AppsRoot | Out-Null

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

# O controle de instancias do launcher (find/close instances + taskkill /T /F)
# agora vive no proprio repo do launcher (app/process.py + app/main_window.py),
# nao mais como patch aplicado aqui. Nada a aplicar: os apps vem direto da
# branch default de cada repo clonado acima.
Write-Host "[prepare_apps] pronto."
