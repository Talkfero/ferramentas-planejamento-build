param(
  # Onde montar o layout de apps/ esperado pelo multi_apps.spec.
  [string]$AppsRoot = (Join-Path (Resolve-Path "$PSScriptRoot\..") "apps"),
  # Raiz onde vivem os repositorios irmaos ja clonados (espelho local).
  [string]$SourceRoot = (Resolve-Path "$PSScriptRoot\..\.."),
  [switch]$Force
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Espelho LOCAL do prepare_apps.ps1: em vez de `git clone` dos repos privados
# no GitHub (precisa de token), copia o working tree dos repositorios irmaos
# ja presentes em $SourceRoot. Assim o "build all" roda 100% offline e nao
# depende do GitHub Actions nem do BUILD_REPO_READ_TOKEN.
#
# Capex foi FUNDIDO no Coplan (capex_engine vendorizado em coplanweb/): nao ha
# mais alvo `capex` — o Coplan Web ja o empacota.
#
# imagedx e unificador NAO entram aqui: sao versionados dentro deste repo
# (apps/imagedx, apps/unificador) e nao devem ser sobrescritos.
# ============================================================================
$repos = @(
  @{ Target = "launcher";              Source = "Ferramenta_plan" },
  @{ Target = "elexplan";              Source = "elexplan" },
  @{ Target = "diagnostico";           Source = "diagnostico_atual" },
  @{ Target = "coplan";                Source = "coplanweb" },
  # status_medicao fundido no Elexplan: sem app/exe/repo proprio.
  @{ Target = "cadastro_viabilidades"; Source = "sistemadecadastro" }
)

# Excludes por NOME (qualquer nivel): seguros de excluir onde quer que apareçam.
# NAO inclui "build"/"dist": coplanweb tem scripts/build/ (coplan_launcher.py,
# Coplan.spec) que e' ESSENCIAL — excluir "build" por nome o apagaria.
$excludeNames = @(
  ".git", "__pycache__", "node_modules",
  ".pytest_cache", ".mypy_cache", ".ruff_cache"
)
# Excludes ANCORADOS na raiz do repo fonte (so o nivel de topo): saida de build
# local e venvs, que sao pesados e irrelevantes — mas so quando estao na raiz.
$excludeRootDirs = @("dist", "build", ".venv", "venv", "env", ".build_venv", ".idea", ".vscode")
$excludeFiles = @("*.pyc", "*.pyo", "*.pdb")

New-Item -ItemType Directory -Force -Path $AppsRoot | Out-Null

foreach ($repo in $repos) {
  $src = Join-Path $SourceRoot $repo.Source
  $dst = Join-Path $AppsRoot $repo.Target

  if (-not (Test-Path $src)) {
    throw "[prepare_apps_local] repo fonte ausente: $src (esperado em $SourceRoot)"
  }

  if (Test-Path $dst) {
    if ($Force) {
      Write-Host "[prepare_apps_local] limpando apps/$($repo.Target)"
      Remove-Item -Recurse -Force $dst
    } else {
      Write-Host "[prepare_apps_local] existe, mantendo: apps/$($repo.Target) (use -Force p/ recopiar)"
      continue
    }
  }

  Write-Host "[prepare_apps_local] copiando $($repo.Source) -> apps/$($repo.Target)"
  # robocopy: rapido, /MIR espelha, /XD exclui dirs, /XF exclui arquivos.
  # /XD aceita NOME (qualquer nivel) e CAMINHO COMPLETO (ancorado na raiz).
  $rootExcl = $excludeRootDirs | ForEach-Object { Join-Path $src $_ }
  $rcArgs = @($src, $dst, "/MIR", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1", "/W:1")
  $rcArgs += "/XD"; $rcArgs += $excludeNames; $rcArgs += $rootExcl
  $rcArgs += "/XF"; $rcArgs += $excludeFiles
  & robocopy @rcArgs | Out-Null
  # robocopy: exit < 8 = sucesso (0=nada novo, 1=copiou, etc.); >= 8 = erro.
  if ($LASTEXITCODE -ge 8) {
    throw "[prepare_apps_local] robocopy falhou ($($repo.Source) -> $($repo.Target)), exit=$LASTEXITCODE"
  }
}

Write-Host "[prepare_apps_local] pronto. Layout montado em $AppsRoot"
