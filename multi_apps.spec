# -*- mode: python ; coding: utf-8 -*-
"""
Spec unica para empacotar os apps compartilhando UM _internal.

Parametrizavel via variavel de ambiente APPS_TO_BUILD:
  APPS_TO_BUILD=all                 -> todos (default)
  APPS_TO_BUILD=launcher            -> apenas o launcher
  APPS_TO_BUILD=launcher,cadastro   -> subconjunto

Chaves validas:
  launcher, elexplan, diag, imagedx, unif, coplan_web, cadastro

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
    'launcher', 'elexplan', 'diag', 'imagedx',
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
DIAG_DIR       = os.path.join(APPS_DIR, "diagnostico")
IMAGEDX_DIR    = os.path.join(APPS_DIR, "imagedx")
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

# Runtime hook compartilhado dos apps pywebview (coplan_web/cadastro):
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
        os.path.join(ELEXPLAN_DIR, "codigo1_elexplan.py"),
        os.path.join(ELEXPLAN_DIR, "Elexplan.ico"),
    ],
    "diag": [
        os.path.join(DIAG_DIR, "diagnostico.py"),
        os.path.join(DIAG_DIR, "diagnostico.ico"),
    ],
    "imagedx": [
        os.path.join(IMAGEDX_DIR, "codigo3_imagedx.py"),
        os.path.join(IMAGEDX_DIR, "eng.ico"),
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
COMMON_EXCLUDES = [
    "tkinter", "_tkinter", "tcl",
    "PyQt5", "PyQt6",
    "matplotlib",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_wxagg",
    "pytest", "doctest", "pydoc",
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

# Leitura de pacote/anexos do Sistema de Cadastro. py7zr tem extensoes e
# dependencias nativas; extract_msg carrega submodulos/datas de forma lazy ao
# abrir e-mails .msg anexados pelo SAP.
CADASTRO_EXTRA_DATAS, CADASTRO_EXTRA_BINARIES, CADASTRO_EXTRA_HIDDEN = _collect_all_safe(
    "py7zr", "extract_msg"
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

    Os modulos Python (backend/, core/, runtime/, shared/) sao detectados
    via static analysis dos imports em main_web.py e nao precisam virar
    datas — PyInstaller os empacota como bytecode em _internal/.
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
    elexplan_entry = os.path.join(ELEXPLAN_DIR, "codigo1_elexplan.py")
    a = Analysis(
        [elexplan_entry],
        pathex=[ROOT, ELEXPLAN_DIR],
        binaries=PIM_EXTRA_BINARIES,
        datas=_existing_datas([
            (os.path.join(ELEXPLAN_DIR, "pim_config.json"), "."),
        ]) + PIM_EXTRA_DATAS,
        hiddenimports=(
            _collect_submodules_safe("pim_backend", extra_paths=[ELEXPLAN_DIR])
            + PIM_EXTRA_HIDDEN
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

if _want('imagedx'):
    a = Analysis(
        [os.path.join(IMAGEDX_DIR, "codigo3_imagedx.py")],
        pathex=[ROOT, IMAGEDX_DIR],
        datas=[],
        hiddenimports=[],
        excludes=COMMON_EXCLUDES,
        cipher=block_cipher,
    )
    _analyses.append(a)
    _exes.append(_mk_exe(a, "ImageDx- Detalhamento",
                         os.path.join(IMAGEDX_DIR, "eng.ico")))

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
            # SAP GUI scripting e fechamento de Excel exportado pelo SAP.
            "win32com.client", "win32gui", "win32con",
            "pythoncom", "pywintypes",
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
