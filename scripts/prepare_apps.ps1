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

Write-Host "[prepare_apps] pronto."
