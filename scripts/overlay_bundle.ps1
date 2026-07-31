<#
.SYNOPSIS
  Completa um bundle recem-compilado (parcial) com o bundle de um build FULL.

.DESCRIPTION
  Serve ao build INCREMENTAL: o PyInstaller recompilou somente alguns apps
  (ex.: coplan_web), entao dist\FerramentasCompartilhadas tem o _internal com
  as dependencias SO desses apps. Este script traz do bundle base (cache do
  ultimo build completo) tudo o que faltou -- os .exe dos outros apps e as
  libs exclusivas deles.

  REGRA: o que o build novo produziu SEMPRE vence. Do base vem apenas o
  arquivo que NAO existe no bundle novo. Por isso o .exe recem-compilado, os
  datas novos (frontend/*.js, index.html...) e qualquer dependencia nova
  ficam intactos.

  Por que isso e' seguro: o cache do bundle base e' chaveado pelo conjunto de
  DEPENDENCIAS (requirements.lock.txt + multi_apps.spec + runtime_hooks +
  os requirements dos apps). Se qualquer um mudar, a chave muda, o cache nao
  bate e o workflow cai para build completo -- entao um arquivo vindo do base
  e' sempre da mesma versao de pacote que o build novo usaria.

  O bundle resultante e' COMPLETO, e isso e' verificado no fim: o
  [InstallDelete] do Setup_turbinado.iss apaga {app}\_internal antes de
  instalar, entao publicar um _internal incompleto deixaria os outros apps ja
  instalados sem as libs deles.

.PARAMETER Base
  Bundle completo restaurado do cache (ex.: bundle_base).

.PARAMETER Fresh
  Bundle recem-compilado, que sera completado in-place
  (ex.: dist\FerramentasCompartilhadas).
#>
param(
    [Parameter(Mandatory = $true)][string]$Base,
    [Parameter(Mandatory = $true)][string]$Fresh
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Base)) {
    throw "[overlay_bundle] bundle base (cache) ausente: $Base"
}
if (-not (Test-Path $Fresh)) {
    throw "[overlay_bundle] bundle recem-compilado ausente: $Fresh"
}

$antes = @(Get-ChildItem -Path $Fresh -Recurse -File -Force).Count
Write-Host "[overlay_bundle] recem-compilado: $antes arquivo(s)"

# robocopy /XC /XN /XO exclui os arquivos classificados como Changed/Newer/
# Older; os identicos ja sao pulados por padrao. Sobra so' o "lonely" -- o que
# existe na origem e NAO no destino. E' exatamente "copiar apenas o que falta",
# e e' MUITO mais rapido que enumerar ~15k arquivos no PowerShell.
$log = Join-Path ([System.IO.Path]::GetTempPath()) ("overlay_{0}.log" -f ([guid]::NewGuid().ToString("N")))
robocopy $Base $Fresh /E /XC /XN /XO /R:2 /W:2 /NFL /NDL /NP /NJH /LOG:$log | Out-Null
$rc = $LASTEXITCODE

# robocopy: < 8 e' sucesso (0 = nada copiado, 1 = copiou, 2 = extras...).
if ($rc -ge 8) {
    if (Test-Path $log) { Get-Content $log | Write-Host }
    Remove-Item $log -Force -ErrorAction SilentlyContinue
    throw "[overlay_bundle] robocopy falhou (exit=$rc)."
}
Remove-Item $log -Force -ErrorAction SilentlyContinue

$depois = @(Get-ChildItem -Path $Fresh -Recurse -File -Force).Count
$vindos = $depois - $antes
Write-Host "[overlay_bundle] apos overlay: $depois arquivo(s) (+$vindos vindos do bundle base)"

# ---------------------------------------------------------------------------
# O bundle TEM de sair completo. Sem esta guarda, um instalador parcial
# apagaria o _internal do usuario e o substituiria por um incompleto.
# ---------------------------------------------------------------------------
$exesEsperados = @(
    "Ferramentas de Planejamento.exe",
    "Elexplan.exe",
    "Diagnostico de alimentadores.exe",
    "Unificador de arquivos.exe",
    "Coplan Web.exe",
    "Sistema de Cadastro.exe"
)

$faltando = @()
foreach ($exe in $exesEsperados) {
    if (-not (Test-Path (Join-Path $Fresh $exe))) { $faltando += $exe }
}
if ($faltando.Count -gt 0) {
    throw ("[overlay_bundle] bundle INCOMPLETO apos o overlay. Executaveis ausentes: " +
           ($faltando -join ", ") + ". O bundle base do cache nao bate com a suite atual.")
}

Write-Host "[overlay_bundle] bundle completo: os $($exesEsperados.Count) executaveis estao presentes."

# robocopy usa exit code como bitmask de SUCESSO (1 = copiou, 2 = havia extras,
# 3 = os dois). Sem zerar isso, o $LASTEXITCODE vaza como codigo de saida do
# script e o passo do GitHub Actions falha mesmo com o overlay correto.
$global:LASTEXITCODE = 0
exit 0
