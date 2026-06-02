param(
    [string]$Token = $env:BUILD_REPO_READ_TOKEN
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Apps = Join-Path $Root "apps"

if (-not $Token) {
    throw "BUILD_REPO_READ_TOKEN ausente. Crie esse secret no repo para clonar os repos privados Talkfero."
}

New-Item -ItemType Directory -Force -Path $Apps | Out-Null

function Clone-App {
    param(
        [Parameter(Mandatory=$true)][string]$Repo,
        [Parameter(Mandatory=$true)][string]$DestName
    )

    $dest = Join-Path $Apps $DestName
    if (Test-Path $dest) {
        Remove-Item -Recurse -Force $dest
    }

    $url = "https://x-access-token:$Token@github.com/$Repo.git"
    git clone --depth 1 $url $dest
}

Clone-App "Talkfero/Ferramenta_plan" "launcher"
Clone-App "Talkfero/elexplan" "elexplan"
Clone-App "Talkfero/diagnostico_atual" "diagnostico"
Clone-App "Talkfero/coplanweb" "coplan"
Clone-App "Talkfero/capex" "capex"
Clone-App "Talkfero/status_medicao" "status_medicoes"
Clone-App "Talkfero/sistemadecadastro" "cadastro_viabilidades"

# O spec antigo espera alguns nomes/posicoes herdados do pacote local.
# Mantemos compatibilidade sem alterar os repos de origem.
$elexLower = Join-Path $Apps "elexplan\codigo1_elexplan.py"
$elexLegacy = Join-Path $Apps "elexplan\codigo1_Elexplan.py"
if ((Test-Path $elexLower) -and -not (Test-Path $elexLegacy)) {
    Copy-Item $elexLower $elexLegacy
}

$coplanIcon = Join-Path $Apps "coplan\frontend\assets\cadastro-de-obras.ico"
$coplanRootIcon = Join-Path $Apps "coplan\cadastro-de-obras.ico"
if ((Test-Path $coplanIcon) -and -not (Test-Path $coplanRootIcon)) {
    Copy-Item $coplanIcon $coplanRootIcon
}

$statusCurrent = Join-Path $Apps "status_medicoes\status_medicao.py"
$statusLegacy = Join-Path $Apps "status_medicoes\codigo8_Status_medicoes.py"
if ((Test-Path $statusCurrent) -and -not (Test-Path $statusLegacy)) {
    Copy-Item $statusCurrent $statusLegacy
}

$required = @(
    "launcher\codigo0_ferramentas_planejamento.py",
    "elexplan\codigo1_elexplan.py",
    "diagnostico\diagnostico.py",
    "imagedx\codigo3_imagedx.py",
    "unificador\codigo4_unificador_de_arquivos.py",
    "coplan\scripts\build\coplan_launcher.py",
    "capex\_nina_ceo\builds\capex_web_launcher.py",
    "status_medicoes\status_medicao.py",
    "cadastro_viabilidades\main_web\main_web.py"
)

$missing = @()
foreach ($rel in $required) {
    $path = Join-Path $Apps $rel
    if (-not (Test-Path $path)) {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    throw "Apps incompletos. Arquivos ausentes: $($missing -join ', ')"
}

Write-Host "Layout pronto em $Apps"
Get-ChildItem $Apps -Directory | Select-Object -ExpandProperty Name
