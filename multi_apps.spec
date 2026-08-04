# -*- mode: python ; coding: utf-8 -*-
"""
Spec unica para empacotar os apps compartilhando UM _internal.

Parametrizavel via variavel de ambiente APPS_TO_BUILD:
  APPS_TO_BUILD=all                 -> todos (default)
  APPS_TO_BUILD=launcher            -> apenas o launcher
  APPS_TO_BUILD=launcher,cadastro   -> subconjunto

Chaves validas:
  launcher, elexplan, diag, unif, coplan_web, cadastro

OBS: o antigo 'capex' (Ambiente Capex.exe) foi FUNDIDO dentro do Coplan
(capex_engine vendorizado em coplanweb/) — virou feature do "Coplan Web.exe".
OBS: o antigo 'status' (Status de medicao.exe) foi FUNDIDO dentro do Elexplan
(abas Chaves/Rebalanceamento + Status Medicoes + Analise Estatistica) — nao ha
mais chave/exe/repo status separado (regra user 2026-06-18). 'status' e' aceito
como alias de 'elexplan'.

Saida:
  dist/FerramentasCompartilhadas/
    _internal/         (compartilhado entre todos os apps selecionados)
    <App>.exe          (um por chave selecionada)
"""

import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules


# =====================================================================
# Selecao de apps
# =====================================================================
VALID_KEYS = {
    'launcher', 'elexplan', 'diag',
    'unif', 'coplan_web', 'cadastro',
}

_apps_env = os.environ.get('APPS_TO_BUILD', 'all').strip().lower()
if _apps_env in ('', 'all'):
    SELECTED_APPS = None  # None = todos
else:
    tokens = {s.strip() for s in _apps_env.replace(';', ',').split(',') if s.strip()}
    if 'all' in tokens:
        SELECTED_APPS = None
    else:
        # Alias retrocompat: 'coplan' antigo (legado PyQt5/PySide6) ja nao
        # existe mais; remapeia para coplan_web pra nao quebrar callers.
        if 'coplan' in tokens:
            tokens.discard('coplan')
            tokens.add('coplan_web')
        # Alias retrocompat: 'capex' foi fundido no Coplan (capex_engine). Um
        # caller pedindo 'capex' agora recebe o coplan_web (que ja o embarca).
        if 'capex' in tokens:
            tokens.discard('capex')
            tokens.add('coplan_web')
        # Alias retrocompat: 'status' (Status de Medicao) foi fundido no
        # Elexplan; remapeia para elexplan.
        if 'status' in tokens:
            tokens.discard('status')
            tokens.add('elexplan')
        invalid = tokens - VALID_KEYS
        if invalid:
            raise SystemExit(
                f"APPS_TO_BUILD contem chaves invalidas: {sorted(invalid)}. "
                f"Chaves validas: {sorted(VALID_KEYS)}"
            )
        SELECTED_APPS = tokens


def _want(key: str) -> bool:
    return SELECTED_APPS is None or key in SELECTED_APPS


# =====================================================================
# STRICT_COLLECT=1 -> pacote que nao coleta DERRUBA o build.
#
# Por padrao _collect_all_safe/_collect_submodules_safe so' AVISAM quando um
# pacote nao esta no venv, para um build parcial de app A nao morrer por causa
# de dependencia do app B. Num build INCREMENTAL isso vira armadilha: o pip
# instala apenas os requirements dos apps recompilados, e um pacote faltando
# sairia so' como print no log -- gerando um .exe com o PYZ incompleto (ex.:
# Build-up do Coplan sem matplotlib/pptx). O overlay com o bundle do cache NAO
# conserta isso, porque os modulos puros viajam DENTRO do .exe recem-gerado.
# Por isso o workflow liga STRICT_COLLECT no modo incremental.
# =====================================================================
STRICT_COLLECT = os.environ.get('STRICT_COLLECT', '').strip().lower() in (
    '1', 'true', 'yes', 'on'
)
if STRICT_COLLECT:
    print("[multi_apps.spec] STRICT_COLLECT=1: coleta que falhar derruba o build.")


print(
    f"[multi_apps.spec] Apps selecionados: "
    f"{'TODOS' if SELECTED_APPS is None else sorted(SELECTED_APPS)}"
)


# =====================================================================
# Caminhos
# =====================================================================
ROOT = os.path.abspath(os.getcwd())
APPS_DIR = os.path.join(ROOT, "apps")

# Cada app mora em apps/<nome>/ com seus .py + icones.
LAUNCHER_DIR   = os.path.join(APPS_DIR, "launcher")
ELEXPLAN_DIR   = os.path.join(APPS_DIR, "elexplan")
# Entry point do Elexplan: a UI DISTRIBUIDA e' a WEB (pywebview), em
# codigo1_web.py -> elexplan.webui.app. O Qt (codigo1_elexplan.py, que importa
# elexplan.frontend.*) foi APOSENTADO em 30/07/2026 e segue no repo apenas como
# legado, empacotado pelo job "build-qt-legacy" do proprio Elexplan.
#
# Ate 31/07/2026 esta spec apontava para codigo1_elexplan.py, entao o
# "Elexplan.exe" da suite abria a janela Qt antiga -- o repo migrou, a receita
# do instalador compartilhado nao. Se for mexer aqui, a receita comprovada e'
# o job "build-web" de .github/workflows/build-exe.yml do repo do Elexplan.
ELEXPLAN_ENTRY = os.path.join(ELEXPLAN_DIR, "codigo1_web.py")
ELEXPLAN_STATIC_DIR = os.path.join(ELEXPLAN_DIR, "elexplan", "webui", "static")
DIAG_DIR       = os.path.join(APPS_DIR, "diagnostico")
UNIF_DIR       = os.path.join(APPS_DIR, "unificador")
COPLAN_DIR     = os.path.join(APPS_DIR, "coplan")
COPLAN_FRONTEND_DIR = os.path.join(COPLAN_DIR, "frontend")
# Entry point frozen do Coplan web: o launcher faz unblock de MOTW e
# reaponta FRONTEND_DIR/HTML_FILE para sys._MEIPASS antes de chamar
# main_web.main(). Apontar direto pro main_web.py quebra os assets no .exe.
COPLAN_LAUNCHER = os.path.join(COPLAN_DIR, "scripts", "build", "coplan_launcher.py")
# Capex foi fundido no Coplan: o motor virou o pacote `capex_engine/` dentro de
# apps/coplan/ (vendorizado). Nao ha mais CAPEX_DIR/exe/launcher proprios — o
# Coplan Web ja o empacota (ver bloco coplan_web e COPLAN_INTERNAL_HIDDEN).
# Status de Medicao foi fundido no Elexplan (abas Chaves/Status/Estatistica);
# nao ha mais STATUS_DIR/exe proprios. O Elexplan ja cobre essas funcoes.
CADASTRO_DIR   = os.path.join(APPS_DIR, "cadastro_viabilidades")
CADASTRO_WEB_DIR = os.path.join(CADASTRO_DIR, "main_web")

DIST_NAME = "FerramentasCompartilhadas"
block_cipher = None

# Runtime hook compartilhado dos apps pywebview (elexplan/coplan_web/cadastro):
# anti-zumbi (os._exit apos fechar janelas) + watchdog anti-congelamento
# (auto-kill se a janela ficar "Nao respondendo" por ~30s). Sem ele, janela
# congelada ignora o "Finalizar tarefa" do Gerenciador e o processo zumbi
# do pythonnet/.NET fica vivo apos fechar. Ver runtime_hooks/pyi_rth_watchdog.py.
RUNTIME_HOOKS_WEB = [os.path.join(ROOT, "runtime_hooks", "pyi_rth_watchdog.py")]


# =====================================================================
# Layout esperado em apps/
# =====================================================================
# O build do GitHub Actions roda scripts/prepare_apps.ps1 para clonar os
# repos reais abaixo. Em build local, esta validacao falha cedo e aponta o
# arquivo faltante, em vez de deixar o PyInstaller quebrar no meio.
APP_REQUIRED_FILES = {
    "launcher": [
        os.path.join(LAUNCHER_DIR, "codigo0_ferramentas_planejamento.py"),
        os.path.join(LAUNCHER_DIR, "eng.ico"),
    ],
    "elexplan": [
        # UI WEB (pywebview) -- e' o Elexplan distribuido desde 30/07/2026.
        # codigo1_elexplan.py (Qt) segue no repo, aposentado, e NAO e' o que
        # entra na suite. Ver ELEXPLAN_ENTRY abaixo.
        os.path.join(ELEXPLAN_DIR, "codigo1_web.py"),
        os.path.join(ELEXPLAN_DIR, "elexplan", "webui", "static", "index.html"),
        os.path.join(ELEXPLAN_DIR, "Elexplan.ico"),
    ],
    "diag": [
        os.path.join(DIAG_DIR, "diagnostico.py"),
        os.path.join(DIAG_DIR, "diagnostico.ico"),
    ],
    "unif": [
        os.path.join(UNIF_DIR, "codigo4_unificador_de_arquivos.py"),
        os.path.join(UNIF_DIR, "Unificador.ico"),
    ],
    "coplan_web": [
        COPLAN_LAUNCHER,
        os.path.join(COPLAN_FRONTEND_DIR, "index.html"),
        os.path.join(COPLAN_FRONTEND_DIR, "assets", "cadastro-de-obras.ico"),
        # Capex embarcado: o motor vendorizado precisa existir no clone do Coplan.
        os.path.join(COPLAN_DIR, "capex_engine", "__init__.py"),
        os.path.join(COPLAN_FRONTEND_DIR, "js", "bridge", "90-capex.js"),
    ],
    "cadastro": [
        os.path.join(CADASTRO_WEB_DIR, "main_web.py"),
        os.path.join(CADASTRO_WEB_DIR, "mw_sap.py"),
        os.path.join(CADASTRO_WEB_DIR, "requirements-web.txt"),
        os.path.join(CADASTRO_WEB_DIR, "index.html"),
        os.path.join(CADASTRO_DIR, "Sistema_Cadastro.ico"),
    ],
}


def _validate_layout():
    missing = []
    for key, files in APP_REQUIRED_FILES.items():
        if not _want(key):
            continue
        for path in files:
            if not os.path.isfile(path):
                missing.append(os.path.relpath(path, ROOT))
    if missing:
        raise SystemExit(
            "[multi_apps.spec] Layout incompleto em apps/. Arquivos ausentes:\n"
            + "\n".join(f"  - {p}" for p in missing)
            + "\n\nRode scripts\\prepare_apps.ps1 no Windows/Actions ou copie os apps "
              "para o layout esperado antes do build."
        )


_validate_layout()


# =====================================================================
# Excludes comuns
# =====================================================================
# NAO excluir "pydoc" daqui: pyqtgraph/parametertree/interactive.py faz
# `import pydoc` no topo do modulo — excluir quebrava o "Grafico de
# Grandezas"/"Curva" do Elexplan em silencio (ImportError generico sem
# dizer que faltava justamente o pydoc, regra user 2026-07-16).
COMMON_EXCLUDES = [
    "tkinter", "_tkinter", "tcl",
    "PyQt5", "PyQt6",
    "matplotlib",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_wxagg",
    "pytest", "doctest",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
]

# Excludes para apps web (pywebview): nao precisa de Qt/PySide6.
WEB_EXCLUDES = [
    "tkinter", "_tkinter", "tcl",
    "PyQt5", "PyQt6", "PySide6",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_wxagg",
    "pytest", "doctest", "pydoc",
]


# =====================================================================
# Coleta de libs de terceiros que NAO sao 100% detectaveis por static
# analysis: pywebview embute DLLs nativas (WebView2) e usa o backend
# .NET via pythonnet/clr_loader (Python.Runtime.dll, ClrLoader.dll). Sem
# COLETAR essas binaries/datas o .exe abre e fecha (ImportError nativo).
# collect_all puxa datas + binaries + hiddenimports de cada pacote.
# =====================================================================
def _collect_all_safe(*pkgs):
    datas, binaries, hiddenimports = [], [], []
    for pkg in pkgs:
        try:
            d, b, h = collect_all(pkg)
        except Exception as exc:  # pacote ausente no venv de build
            if STRICT_COLLECT:
                raise SystemExit(
                    f"[multi_apps.spec] collect_all({pkg!r}) falhou: {exc}\n"
                    "STRICT_COLLECT=1 (build incremental): o pacote PRECISA estar "
                    "instalado. O bundle do cache nao conserta um PYZ incompleto "
                    "dentro do .exe recem-gerado. Confira o requirements do app "
                    "recompilado."
                ) from exc
            print(f"[multi_apps.spec] collect_all({pkg!r}) falhou: {exc}")
            continue
        datas += d
        binaries += b
        hiddenimports += h
    return datas, binaries, hiddenimports


def _collect_submodules_safe(*pkgs, extra_paths=()):
    """collect_submodules de cada pkg, tolerando ausencia.

    ``extra_paths`` sao inseridos TEMPORARIAMENTE no inicio do sys.path
    durante a coleta. Necessario porque os pacotes do Coplan
    (backend/core/runtime/shared) moram em apps/coplan/ -- nao na raiz onde
    o PyInstaller roda o spec. Sem isso, collect_submodules nao encontra
    esses pacotes no parse, cai no except e retorna [] (rede de seguranca
    vazia), deixando modulos lazy fora do bundle -> "DatabaseManager
    indisponivel" no runtime. O sys.path e' restaurado no finally.
    """
    added = [p for p in extra_paths
             if p and p not in sys.path and os.path.isdir(p)]
    for p in added:
        sys.path.insert(0, p)
    try:
        hiddenimports = []
        for pkg in pkgs:
            try:
                hiddenimports += collect_submodules(pkg)
            except Exception as exc:
                if STRICT_COLLECT:
                    raise SystemExit(
                        f"[multi_apps.spec] collect_submodules({pkg!r}) falhou: "
                        f"{exc}\nSTRICT_COLLECT=1 (build incremental): sem esses "
                        "submodulos o .exe sai com o grafo de modulos furado."
                    ) from exc
                print(f"[multi_apps.spec] collect_submodules({pkg!r}) falhou: {exc}")
        return hiddenimports
    finally:
        for p in added:
            try:
                sys.path.remove(p)
            except ValueError:
                pass


# pywebview + backend .NET (Windows EdgeChromium/WebView2). Necessario
# para os dois apps web (coplan_web, cadastro).
WEBVIEW_DATAS, WEBVIEW_BINARIES, WEBVIEW_HIDDEN = _collect_all_safe(
    "webview", "clr_loader", "pythonnet"
)

# Leitura de pacote/anexos do Sistema de Cadastro. py7zr tem codecs/deps
# nativas; extract_msg carrega submodulos/datas de forma lazy ao abrir e-mails
# .msg anexados pelo SAP. Sentence Transformers/ONNX e o fallback local para
# formularios e normas que os parsers deterministas ainda nao reconhecem.
CADASTRO_EXTRA_DATAS, CADASTRO_EXTRA_BINARIES, CADASTRO_EXTRA_HIDDEN = _collect_all_safe(
    "py7zr",
    "Cryptodome",
    "pyppmd",
    "pybcj",
    "multivolumefile",
    "inflate64",
    "brotli",
    "backports.zstd",
    "extract_msg",
    "sentence_transformers",
    "transformers",
    "optimum",
    "onnxruntime",
    "tokenizers",
    # Snowflake: atualizacao automatica da Reserva Tecnica e a aba Consulta
    # (sucede o Oracle, desligado). O import e lazy em
    # mw_snowflake.conectar(), e o driver carrega backends/certificados que o
    # PyInstaller nao enxerga sozinho -> collect_all.
    "snowflake",
)

PIM_EXTRA_DATAS, PIM_EXTRA_BINARIES, PIM_EXTRA_HIDDEN = _collect_all_safe(
    "playwright"
)
PIM_EXTRA_DATAS = [
    item for item in PIM_EXTRA_DATAS
    if ".local-browsers" not in str(item[0]).replace("\\", "/")
]
PIM_EXTRA_BINARIES = [
    item for item in PIM_EXTRA_BINARIES
    if ".local-browsers" not in str(item[0]).replace("\\", "/")
]

# Extras do Build-up do Coplan (motor CAPEX embarcado): python-pptx embute o
# template default.pptx (datas) e matplotlib/numpy precisam de mpl-data + C
# extensions. Sao lazy-import em capex_engine/backend/buildup_pptx.py (so quando
# o usuario exporta o Build-up); o collect_all garante mpl-data/ft2font/numpy
# no bundle frozen. Espelha o build do proprio Coplan (scripts/build/Coplan.spec).
COPLAN_EXTRA_DATAS, COPLAN_EXTRA_BINARIES, COPLAN_EXTRA_HIDDEN = _collect_all_safe(
    "pptx", "matplotlib", "numpy", "pyparsing"
)

# COPLAN_DIR no path para a coleta achar backend/core/runtime/shared/capex_engine
# do Coplan (vivem em apps/coplan/, nao na raiz). Forca TODO submodulo desses
# pacotes como hiddenimport -- blinda contra imports lazy (core.exceptions,
# core.services.apoio_service, core.repositories.excel_cache, shared.*,
# capex_engine.* importado lazy pelo CapexMixin) que a analise estatica do
# PyInstaller nao segue de dentro de metodos.
COPLAN_INTERNAL_HIDDEN = _collect_submodules_safe(
    "backend", "core", "runtime", "shared", "capex_engine", extra_paths=[COPLAN_DIR]
)
print(
    f"[multi_apps.spec] COPLAN_INTERNAL_HIDDEN: "
    f"{len(COPLAN_INTERNAL_HIDDEN)} submodulos coletados"
)

CADASTRO_INTERNAL_HIDDEN = [
    "local_server",
    "webview_shim",
    "mw_backup",
    "mw_base",
    "mw_config",
    "mw_secret",
    "mw_db",
    "mw_despacho",
    "mw_email",
    "mw_feriados",
    "mw_formulario",
    "mw_layout",
    "mw_lock",
    "mw_mapatermico",
    "mw_notas",
    "mw_obras",
    "mw_pathwrite",
    "mw_prazos",
    "mw_reservas",
    "mw_resolve",
    "mw_schema",
    "mw_sources",
    "mw_sap",
    "mw_text",
    "mw_validacao",
    "api_config_visual",
    "api_demandas",
    "api_despacho",
    "api_email",
    "api_excel",
    "api_fontes",
    "api_formulario",
    "api_mapa_termico",
    "api_notif",
    "api_obras",
    "api_oracle",
    "api_primeira_medida",
    "api_relatorios",
    "api_reservas",
    "api_sistema",
    "api_viabilidades",
]


# =====================================================================
# Datas — assets estaticos (HTML/JS/CSS/ICO) preservando subpastas
# =====================================================================
def _coplan_web_datas():
    """Frontend do Coplan web (pywebview).

    Estrutura no bundle:
      _internal/frontend/index.html
      _internal/frontend/assets/cadastro-de-obras.ico
      _internal/frontend/js/bridge/*.js
      _internal/capex_engine/assets/logo_equatorial.png

    Os modulos Python (backend/, core/, runtime/, shared/) sao detectados
    via static analysis dos imports em main_web.py e nao precisam virar
    datas — PyInstaller os empacota como bytecode em _internal/.

    Logo da aba "Obras" do Excel de cenario (capex_engine/backend/
    excel_format.py::_obras_logo_path, regra user 2026-07-14): unico
    asset binario do capex_engine, nao detectavel por static analysis.
    Sem isso a logo simplesmente nao aparece na exportacao (best-effort,
    nao derruba o export) — sumiu no instalador compartilhado porque este
    spec e' separado do coplanweb/scripts/build/Coplan.spec (que ja tem
    o datas equivalente).
    """
    datas = []
    index = os.path.join(COPLAN_FRONTEND_DIR, "index.html")
    if os.path.isfile(index):
        datas.append((index, "frontend"))
    for asset in glob.glob(os.path.join(COPLAN_FRONTEND_DIR, "assets", "*")):
        if os.path.isfile(asset):
            datas.append((asset, os.path.join("frontend", "assets")))
    for js in glob.glob(os.path.join(COPLAN_FRONTEND_DIR, "js", "bridge", "*.js")):
        datas.append((js, os.path.join("frontend", "js", "bridge")))
    for asset in glob.glob(os.path.join(COPLAN_DIR, "capex_engine", "assets", "*")):
        if os.path.isfile(asset):
            datas.append((asset, os.path.join("capex_engine", "assets")))
    return datas


def _elexplan_web_datas():
    """Frontend web do Elexplan (pywebview) + docs que a UI abre.

    Espelha os `--add-data` do job **build-web** de
    `.github/workflows/build-exe.yml` no repo do Elexplan -- a receita
    comprovada do `Elexplan_Setup.exe`. Estrutura no bundle:

      _internal/Elexplan.ico
      _internal/pim_config.json
      _internal/docs/CRITERIOS_DE_CALCULO.md
      _internal/docs/FORMATO_DE_ARQUIVOS.md
      _internal/elexplan/webui/static/**   (index.html, css/, js/, vendor/uPlot)

    Sem o `static/` a janela do pywebview abre EM BRANCO: HTML/CSS/JS nao sao
    modulos Python, entao a analise estatica do PyInstaller nao os enxerga.
    """
    datas = []
    for src, dst in (
        (os.path.join(ELEXPLAN_DIR, "Elexplan.ico"), "."),
        (os.path.join(ELEXPLAN_DIR, "pim_config.json"), "."),
        (os.path.join(ELEXPLAN_DIR, "docs", "CRITERIOS_DE_CALCULO.md"), "docs"),
        (os.path.join(ELEXPLAN_DIR, "docs", "FORMATO_DE_ARQUIVOS.md"), "docs"),
    ):
        if os.path.isfile(src):
            datas.append((src, dst))

    # Arvore completa do static/ preservando as subpastas (css, js, vendor).
    for dirpath, _dirnames, filenames in os.walk(ELEXPLAN_STATIC_DIR):
        destino = os.path.relpath(dirpath, ELEXPLAN_DIR)
        for nome in filenames:
            datas.append((os.path.join(dirpath, nome), destino))
    return datas


def _cadastro_datas():
    """Frontend do Cadastro web (pywebview).

    Tudo no nivel raiz do bundle (`.`) porque main_web.py faz
    `HERE = Path(__file__).resolve().parent` e procura index.html ao lado.
    Em frozen, HERE == _MEIPASS.
    """
    datas = []
    for pattern in ("*.html", "*.js", "*.css"):
        for f in glob.glob(os.path.join(CADASTRO_WEB_DIR, pattern)):
            datas.append((f, "."))
    return datas


# =====================================================================
# Criacao condicional de Analysis/EXE
# =====================================================================
_analyses: list = []
_exes: list = []


# ---------------------------------------------------------------------------
# Metadados de versao (VSVersionInfo) por executavel.
#
# Ate 04/08/2026 os seis .exe saiam SEM nenhum metadado: FileVersion,
# ProductName e CompanyName vazios (o unico com identidade era o unins000.exe,
# que o Inno gera). Binario anonimo + sem assinatura + comportamento de lancar
# outros processos e' o retrato que a heuristica do Defender marca -- foi o
# `Ferramentas de Planejamento.exe` (2 MB, so' spawna processos) que passou a
# ser bloqueado com ERROR_VIRUS_INFECTED (225) no 1.2.1.
#
# Preencher isto nao substitui a assinatura Authenticode, mas tira o binario
# da categoria "executavel anonimo desconhecido" e declara corretamente quem
# publica o que. A versao vem de APP_VERSION (o workflow passa a mesma do
# .iss); sem ela, cai no default e o build nao quebra.
# ---------------------------------------------------------------------------
SUITE_VERSION = os.environ.get("APP_VERSION", "").strip() or "0.0.0"
SUITE_COMPANY = "Arthur Cardoso"
SUITE_NAME = "Ferramentas de Planejamento"


def _version_tuple(texto):
    partes = []
    for pedaco in str(texto).split("."):
        digitos = "".join(c for c in pedaco if c.isdigit())
        partes.append(int(digitos) if digitos else 0)
    while len(partes) < 4:
        partes.append(0)
    return tuple(partes[:4])


def _mk_version_info(nome_exe):
    """VSVersionInfo do PyInstaller. `None` se a API nao existir (o build
    segue sem metadado em vez de falhar)."""
    try:
        from PyInstaller.utils.win32.versioninfo import (
            FixedFileInfo, StringFileInfo, StringStruct, StringTable,
            VarFileInfo, VarStruct, VSVersionInfo,
        )
    except Exception:  # noqa: BLE001
        return None
    v = _version_tuple(SUITE_VERSION)
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=v, prodvers=v, mask=0x3F, flags=0x0,
                          OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", SUITE_COMPANY),
                # O launcher se chama igual a suite; sem isto a descricao
                # sairia "Ferramentas de Planejamento - Ferramentas de
                # Planejamento" nas propriedades do arquivo.
                StringStruct("FileDescription",
                             nome_exe if nome_exe == SUITE_NAME
                             else f"{nome_exe} - {SUITE_NAME}"),
                StringStruct("FileVersion", SUITE_VERSION),
                StringStruct("InternalName", nome_exe),
                StringStruct("LegalCopyright", f"(c) {SUITE_COMPANY}"),
                StringStruct("OriginalFilename", f"{nome_exe}.exe"),
                StringStruct("ProductName", SUITE_NAME),
                StringStruct("ProductVersion", SUITE_VERSION),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )


def _mk_exe(analysis, name, icon):
    pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)
    return EXE(
        pyz,
        analysis.scripts,
        [],
        exclude_binaries=True,
        name=name,
        icon=icon,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        version=_mk_version_info(name),
    )


def _existing_datas(items):
    return [(src, dst) for src, dst in items if os.path.isfile(src)]


if _want('launcher'):
    a = Analysis(
        [os.path.join(LAUNCHER_DIR, "codigo0_ferramentas_planejamento.py")],
        pathex=[ROOT, LAUNCHER_DIR],
        binaries=[],
        datas=_existing_datas([
            (os.path.join(LAUNCHER_DIR, "eng.png"), "."),
            (os.path.join(LAUNCHER_DIR, "icone.png"), "."),
        ]),
        hiddenimports=[],
        hookspath=[],
        runtime_hooks=[],
        excludes=COMMON_EXCLUDES,
        cipher=block_cipher,
        noarchive=False,
    )
    _analyses.append(a)
    _exes.append(_mk_exe(a, "Ferramentas de Planejamento",
                         os.path.join(LAUNCHER_DIR, "eng.ico")))

if _want('elexplan'):
    # Elexplan WEB (pywebview), nao o Qt legado -- ver ELEXPLAN_ENTRY.
    # Precisa das mesmas pecas dos outros apps pywebview da suite:
    # collect_all de webview/pythonnet/clr_loader (DLLs nativas do WebView2 e
    # do backend .NET, invisiveis para a analise estatica) e o runtime hook
    # anti-zumbi. Sem o collect_all, o .exe abre e fecha (ImportError nativo).
    a = Analysis(
        [ELEXPLAN_ENTRY],
        pathex=[ROOT, ELEXPLAN_DIR],
        binaries=PIM_EXTRA_BINARIES + WEBVIEW_BINARIES,
        datas=_elexplan_web_datas() + PIM_EXTRA_DATAS + WEBVIEW_DATAS,
        runtime_hooks=RUNTIME_HOOKS_WEB,
        hiddenimports=(
            ["webview"]
            + _collect_submodules_safe("pim_backend", extra_paths=[ELEXPLAN_DIR])
            # A UI web importa os modulos de elexplan.webui/backend de forma
            # indireta (registro de abas, jobs); blinda contra o que a analise
            # estatica nao segue de dentro de metodos.
            + _collect_submodules_safe(
                "elexplan.webui", "elexplan.backend", extra_paths=[ELEXPLAN_DIR]
            )
            + PIM_EXTRA_HIDDEN
            + WEBVIEW_HIDDEN
        ),
        excludes=COMMON_EXCLUDES,
        cipher=block_cipher,
    )
    _analyses.append(a)
    _exes.append(_mk_exe(a, "Elexplan",
                         os.path.join(ELEXPLAN_DIR, "Elexplan.ico")))

if _want('diag'):
    # Entry point renomeado: era codigo2_diagnostico_atual.py, agora
    # diagnostico.py. Nome do exe preservado ("Diagnostico de
    # alimentadores") para nao quebrar atalhos/uninstaller existentes.
    a = Analysis(
        [os.path.join(DIAG_DIR, "diagnostico.py")],
        pathex=[ROOT, DIAG_DIR],
        datas=[],
        hiddenimports=[
            "secrets",
            "pandas",
            "pandas.io.formats.excel",
            "xlsxwriter",
            "openpyxl",
        ],
        excludes=COMMON_EXCLUDES,
        cipher=block_cipher,
    )
    _analyses.append(a)
    _exes.append(_mk_exe(a, "Diagnostico de alimentadores",
                         os.path.join(DIAG_DIR, "diagnostico.ico")))

if _want('unif'):
    a = Analysis(
        [os.path.join(UNIF_DIR, "codigo4_unificador_de_arquivos.py")],
        pathex=[ROOT, UNIF_DIR],
        datas=[],
        hiddenimports=["chardet", "openpyxl", "secrets"],
        excludes=COMMON_EXCLUDES,
        cipher=block_cipher,
    )
    _analyses.append(a)
    _exes.append(_mk_exe(a, "Unificador de arquivos",
                         os.path.join(UNIF_DIR, "Unificador.ico")))

if _want('coplan_web'):
    # Coplan web (pywebview): entry point e' o coplan_launcher.py (faz
    # unblock MOTW + reaponta FRONTEND_DIR/HTML_FILE pra _MEIPASS) que
    # chama main_web.main(). main_web importa backend.api (-> backend.
    # domains.*), core.*, runtime.*, shared.*; pathex=COPLAN_DIR resolve.
    # Frontend (HTML/JS/icone) entra como datas em `frontend/...`.
    #
    # OBS: o legado PySide6 (legacy_desktop/codigo5_coplan.py) NAO e' mais
    # empacotado — foi removido do bundle a pedido do operador.
    a = Analysis(
        [COPLAN_LAUNCHER],
        pathex=[ROOT, COPLAN_DIR],
        binaries=WEBVIEW_BINARIES + COPLAN_EXTRA_BINARIES,
        datas=_coplan_web_datas() + WEBVIEW_DATAS + COPLAN_EXTRA_DATAS,
        runtime_hooks=RUNTIME_HOOKS_WEB,
        hiddenimports=[
            "webview",
            "main_web",
            "pandas", "openpyxl", "sqlite3", "secrets",
            # Motor CAPEX embarcado (Gerenciador de Cenarios) + Build-up.
            # CapexMixin importa capex_engine de forma lazy (dentro de metodos);
            # buildup_pptx faz lazy-import de matplotlib/pptx ao exportar.
            "pptx", "matplotlib",
            "capex_engine",
            "capex_engine.main_web",
            "capex_engine.backend.api",
            "capex_engine.backend.buildup_pptx",
            # Domains do backend sao importados estaticamente em
            # backend.api, mas explicitamos pra robustez frente a
            # refactors que troquem imports por importlib.
            "backend.api",
            "backend._state",
            "backend.domains.core",
            "backend.domains.obras",
            "backend.domains.apoio",
            "backend.domains.valor",
            "backend.domains.cadastro",
            "backend.domains.tecnico",
            "backend.domains.ganhos",
            "backend.domains.criterios",
            "backend.domains.resumos",
            "backend.domains.config",
            "backend.domains.banco",
            "backend.domains.calc",
            "backend.domains.nota_colapso",
            "backend.domains.cenarios",
            "backend.domains.validacoes",
            # Runtime usado por CoreMixin._ensure_managers(). Quando o
            # PyInstaller deixa algum destes de fora, a UI recebe
            # "DatabaseManager indisponivel" ao tentar conectar o banco.
            "runtime.apoio",
            "runtime.calc",
            "runtime.config",
            "runtime.database",
            "runtime.notify",
            "runtime.pi_base",
            "runtime.text_utils",
            "core.repositories.sqlite_connection",
            "core.repositories.sqlite_lock",
            "core.repositories.sqlite_schema",
            "core.repositories.obra_read_repo",
            "core.repositories.obra_query_repo",
            "core.repositories.obra_sql_helpers",
            "core.repositories.excel_cache",
            "core.services.atualizar_obra_service",
            "core.services.apoio_service",
            "core.services.nota_colapso_service",
            "core.services.obra_rules",
            "core.services.pi_metadata_service",
            "core.services.relatorio_criterios_service",
            "core.services.resumo_service",
            "core.services.row_helpers",
            "core.services.salvar_obra_service",
            # Imports lazy (dentro de metodos) que a analise estatica do
            # PyInstaller nao seguia -- carregados no boot por _ensure_managers
            # (apoio/calc) e pelo grafo de runtime.*. Sem eles: import falha
            # no .exe -> "DatabaseManager indisponivel".
            "core.exceptions",
            "core.models",
            "shared.texto_utils",
        ] + WEBVIEW_HIDDEN + COPLAN_INTERNAL_HIDDEN + COPLAN_EXTRA_HIDDEN,
        excludes=WEB_EXCLUDES,
        cipher=block_cipher,
    )
    _analyses.append(a)
    _exes.append(_mk_exe(a, "Coplan Web",
                         os.path.join(COPLAN_FRONTEND_DIR, "assets", "cadastro-de-obras.ico")))

# NOTA: o antigo bloco `if _want('capex'):` (Ambiente Capex.exe) foi removido.
# O Capex agora e' empacotado DENTRO do "Coplan Web" via capex_engine + os
# COLLECT de matplotlib/numpy/pptx acima. Nao ha mais exe/chave capex separados.

# NOTA: o antigo bloco `if _want('status'):` (Status de medicao.exe) foi
# removido. As funcoes de Status de Medicao (chaves/rebalanceamento, status PIM
# por alimentador e analise estatistica) foram fundidas no Elexplan como abas.
# Nao ha mais exe/chave status separados ('status' e' alias de 'elexplan').

if _want('cadastro'):
    # Cadastro web (pywebview puro): main_web.py + index.html + JS/CSS.
    # NAO usa mais local_server.py/webview_shim.py (extintos) nem tkinter
    # (dialogs via pywebview.create_file_dialog). main_web.py resolve os
    # assets via Path(__file__).parent; em frozen __file__ cai em _MEIPASS,
    # entao os datas vao para a raiz (`.`) do bundle. Sem launcher proprio:
    # nao precisa reapontar paths (root-relative ja casa com _MEIPASS).
    a = Analysis(
        [os.path.join(CADASTRO_WEB_DIR, "main_web.py")],
        pathex=[ROOT, CADASTRO_WEB_DIR],
        binaries=WEBVIEW_BINARIES + CADASTRO_EXTRA_BINARIES,
        datas=_cadastro_datas() + WEBVIEW_DATAS + CADASTRO_EXTRA_DATAS,
        runtime_hooks=RUNTIME_HOOKS_WEB,
        hiddenimports=[
            "webview",
            "pandas", "openpyxl", "sqlite3",
            # Leitura de formularios/pacotes e e-mails anexados.
            "pypdf", "py7zr", "extract_msg",
            "sentence_transformers", "transformers", "optimum", "onnxruntime",
            # SAP GUI scripting e fechamento de Excel exportado pelo SAP.
            "win32com.client", "win32gui", "win32con",
            "pythoncom", "pywintypes",
            # Consulta ao Snowflake (Reserva Tecnica + aba Consulta).
            "snowflake.connector",
        ] + WEBVIEW_HIDDEN + CADASTRO_INTERNAL_HIDDEN + CADASTRO_EXTRA_HIDDEN,
        excludes=[
            "PyQt5", "PyQt6", "PySide6",
            "matplotlib.backends.backend_tkagg",
            "matplotlib.backends.backend_gtk3agg",
            "matplotlib.backends.backend_wxagg",
            "pytest", "doctest", "pydoc",
        ],
        cipher=block_cipher,
    )
    _analyses.append(a)
    _exes.append(_mk_exe(a, "Sistema de Cadastro",
                         os.path.join(CADASTRO_DIR, "Sistema_Cadastro.ico")))


if not _exes:
    raise SystemExit(
        f"Nenhum app selecionado. APPS_TO_BUILD='{_apps_env}'. "
        f"Chaves validas: {sorted(VALID_KEYS)}"
    )


# =====================================================================
# COLLECT compartilhado — DLLs, libs Python e datas em UM _internal
# =====================================================================
def _sum(attr):
    total = []
    for a in _analyses:
        total += getattr(a, attr)
    return total


coll = COLLECT(
    *_exes,
    _sum("binaries"),
    _sum("zipfiles"),
    _sum("datas"),
    strip=False,
    upx=False,
    upx_exclude=[],
    name=DIST_NAME,
)
