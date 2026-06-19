# -*- coding: utf-8 -*-
"""
build_gui.py — Gerador de executáveis (PySide6).

Interface gráfica para escolher quais apps compilar e opcionalmente
gerar o instalador (Inno Setup) logo em seguida.

Uso:
    python build_gui.py

Funcionalidades:
  - Checkbox por app (lê a lista abaixo)
  - Persistência da última seleção em .build_gui_state.json
  - Execução do PyInstaller em processo separado (UI não trava)
  - Log em tempo real (stdout + stderr) na janela
  - Botão "Cancelar" interrompe o build
  - Se só 1 app for selecionado, oferece /DAPP_ONLY ao compilar o ISS
  - Botão para abrir a pasta dist/ ou Output/ ao final
"""

import json
import os
import shutil
import sys
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QSize, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)


APP_TITLE = "Build - Ferramentas de Planejamento"
APP_VERSION = "1.0"

ROOT = os.path.dirname(os.path.abspath(__file__))
SPEC_FILE = os.path.join(ROOT, "multi_apps.spec")
ISS_FILE = os.path.join(ROOT, "Setup_turbinado.iss")
DIST_DIR = os.path.join(ROOT, "dist", "FerramentasCompartilhadas")
OUTPUT_DIR = os.path.join(ROOT, "Output")
STATE_FILE = os.path.join(ROOT, ".build_gui_state.json")


@dataclass(frozen=True)
class AppDef:
    key: str            # chave usada em APPS_TO_BUILD / /DAPP_ONLY
    title: str          # texto exibido
    subtitle: str       # descrição curta
    script: str         # caminho do .py (só p/ tooltip)
    icon: str           # caminho do .ico (display)


APPS: List[AppDef] = [
    AppDef("launcher", "Ferramentas de Planejamento (launcher)",
           "Menu central, busca, favoritos e atalhos",
           "apps/launcher/codigo0_ferramentas_planejamento.py",
           "apps/launcher/eng.ico"),
    AppDef("elexplan", "Elexplan",
           "Parâmetros elétricos + Status de Medição (chaves, status PIM, estatística)",
           "apps/elexplan/codigo1_elexplan.py",
           "apps/elexplan/Elexplan.ico"),
    AppDef("diag", "Diagnóstico de alimentadores",
           "Relatórios e diagnósticos da rede",
           "apps/diagnostico/diagnostico.py",
           "apps/diagnostico/diagnostico.ico"),
    AppDef("imagedx", "ImageDx — Detalhamento",
           "Detalhamento visual",
           "apps/imagedx/codigo3_imagedx.py",
           "apps/imagedx/eng.ico"),
    AppDef("unif", "Unificador de arquivos",
           "Junta planilhas e CSVs",
           "apps/unificador/codigo4_unificador_de_arquivos.py",
           "apps/unificador/Unificador.ico"),
    AppDef("coplan_web", "Coplan Web",
           "Cadastro de obras + Gerenciador de Cenários/CAPEX (pywebview)",
           "apps/coplan/main_web.py",
           "apps/coplan/frontend/assets/cadastro-de-obras.ico"),
    AppDef("cadastro", "Sistema de Cadastro",
           "Cadastro de viabilidades técnicas (pywebview)",
           "apps/cadastro_viabilidades/main_web/main_web.py",
           "apps/cadastro_viabilidades/Sistema_Cadastro.ico"),
]


# =====================================================================
# Dependências por app (passo pré-PyInstaller). Espelha :install_for de
# build_all_shared.bat. Apps web usam o requirements-web.txt (NÃO o
# requirements.txt desktop da raiz); apps sem arquivo recebem os pacotes
# inline. Defina a env var SKIP_DEPS=1 para pular a instalação.
# =====================================================================
APP_REQ_FILES = {
    "launcher":   "apps/launcher/requirements.txt",
    "diag":       "apps/diagnostico/requirements.txt",
    "coplan_web": "apps/coplan/requirements-web.txt",
    "cadastro":   "apps/cadastro_viabilidades/main_web/requirements-web.txt",
    # imagedx e unif tem requirements.txt PINADO (versoes ==) versionado aqui.
    "imagedx":    "apps/imagedx/requirements.txt",
    "unif":       "apps/unificador/requirements.txt",
    # Elexplan inclui o Status de Medicao (usa openpyxl p/ XLSX de chaves).
    "elexplan":   "apps/elexplan/requirements.txt",
}
APP_REQ_PKGS = {
    "coplan_web": ["pythonnet", "clr_loader"],
    "cadastro": ["pythonnet", "clr_loader"],
}


# =====================================================================
# Estilo (corporativo, alinhado com o launcher)
# =====================================================================
QSS = """
QMainWindow { background: #F1F4F9; }
QWidget { color: #1F2937; font-size: 12px; }

QLabel#HeaderTitle {
    font-size: 18px; font-weight: 700; color: #0B1220;
}
QLabel#HeaderSubtitle { font-size: 12px; color: #64748B; }

QFrame#HeaderBar, QFrame#Card {
    background: #FFFFFF; border: 1px solid #E1E5ED; border-radius: 12px;
}

QCheckBox {
    padding: 8px; border: 1px solid #E1E5ED; border-radius: 10px;
    background: #FFFFFF;
}
QCheckBox:hover { border-color: #B8C3D6; background: #FBFCFE; }
QCheckBox:checked { border-color: #1D4ED8; background: #EFF4FF; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF;
}
QCheckBox::indicator:hover { border-color: #1D4ED8; }
QCheckBox::indicator:checked {
    background: #1D4ED8; border-color: #1D4ED8;
    image: none;
}

QPushButton[class="Primary"] {
    background: #1D4ED8; color: #FFFFFF; border: none; border-radius: 8px;
    padding: 9px 14px; font-weight: 600; min-width: 110px;
}
QPushButton[class="Primary"]:hover   { background: #1E40AF; }
QPushButton[class="Primary"]:pressed { background: #1E3A8A; }
QPushButton[class="Primary"]:disabled { background: #94A3B8; color: #F8FAFC; }

QPushButton[class="Ghost"] {
    background: transparent; border: 1px solid #D3D9E4; color: #1F2937;
    border-radius: 8px; padding: 8px 12px; font-weight: 600;
}
QPushButton[class="Ghost"]:hover { background: #EEF2F8; border-color: #B5BECD; }
QPushButton[class="Ghost"]:disabled { color: #94A3B8; }

QPushButton[class="Danger"] {
    background: transparent; color: #B91C1C; border: 1px solid #F5C2C7;
    border-radius: 8px; padding: 8px 12px; font-weight: 600;
}
QPushButton[class="Danger"]:hover { background: #FEE2E2; }

QTextEdit#Log {
    background: #0B1220; color: #E2E8F0;
    border: 1px solid #1F2937; border-radius: 8px;
    font-family: Consolas, "Courier New", monospace; font-size: 11px;
}

QProgressBar {
    background: #EEF2F8; border: 1px solid #D3D9E4; border-radius: 6px;
    text-align: center; color: #0B1220; height: 14px;
}
QProgressBar::chunk { background: #1D4ED8; border-radius: 6px; }

QLabel#StatusLabel { color: #64748B; font-size: 11px; }

QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical {
    background: #D3D9E4; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #A9B3C6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QLabel#FooterHint { color: #94A3B8; font-size: 11px; }
"""


# =====================================================================
# Persistência de estado (última seleção + última opção)
# =====================================================================
def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# =====================================================================
# Janela principal
# =====================================================================
class BuildWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(960, 680)

        icn = os.path.join(ROOT, "apps", "launcher", "eng.ico")
        if os.path.exists(icn):
            self.setWindowIcon(QIcon(icn))

        self.state = load_state()
        self._process: Optional[QProcess] = None
        self._stage: str = "idle"   # idle | deps | pyinstaller | iscc
        self._pending_iss: bool = False
        self._dep_queue: List[tuple] = []   # fila de (label, args do pip)
        self._dep_apps_value: str = ""      # APPS_TO_BUILD apos as deps

        self._build_ui()
        self._apply_saved_selection()
        self.setStyleSheet(QSS)

    # ---------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        root.addWidget(self._build_header())

        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self._build_apps_card())
        split.addWidget(self._build_log_card())
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        split.setHandleWidth(6)
        root.addWidget(split, 1)

        root.addWidget(self._build_footer())

        self.statusBar().showMessage("Pronto.")
        self._build_actions()

    def _build_header(self) -> QWidget:
        h = QFrame()
        h.setObjectName("HeaderBar")
        lay = QHBoxLayout(h)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)

        icon_path = os.path.join(ROOT, "apps", "launcher", "eng.png")
        if os.path.exists(icon_path):
            lbl = QLabel()
            from PySide6.QtGui import QPixmap
            lbl.setPixmap(QPixmap(icon_path).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
            lay.addWidget(lbl)

        box = QVBoxLayout()
        box.setSpacing(2)
        t1 = QLabel(APP_TITLE)
        t1.setObjectName("HeaderTitle")
        t2 = QLabel(
            "Selecione os apps que deseja compilar e clique em "
            "\"Compilar selecionados\". O PyInstaller vai rodar em "
            "segundo plano; o log aparece abaixo."
        )
        t2.setObjectName("HeaderSubtitle")
        t2.setWordWrap(True)
        box.addWidget(t1)
        box.addWidget(t2)
        lay.addLayout(box, 1)

        return h

    def _build_apps_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(14, 14, 14, 14)
        card_lay.setSpacing(10)

        row_top = QHBoxLayout()
        row_top.setSpacing(8)
        row_top.addWidget(QLabel("Apps disponíveis:"))
        row_top.addStretch(1)

        btn_all = QPushButton("Selecionar todos")
        btn_all.setProperty("class", "Ghost")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.clicked.connect(lambda: self._set_all(True))
        row_top.addWidget(btn_all)

        btn_none = QPushButton("Limpar seleção")
        btn_none.setProperty("class", "Ghost")
        btn_none.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_none.clicked.connect(lambda: self._set_all(False))
        row_top.addWidget(btn_none)

        card_lay.addLayout(row_top)

        # Scroll com checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        host = QWidget()
        host_lay = QVBoxLayout(host)
        host_lay.setContentsMargins(0, 0, 0, 0)
        host_lay.setSpacing(8)

        self._checkboxes: List[QCheckBox] = []
        for a in APPS:
            cb = QCheckBox()
            cb.setProperty("app_key", a.key)
            label = f"{a.title}\n  {a.subtitle}"
            cb.setText(label)
            cb.setToolTip(f"Script: {a.script}")
            cb.setFont(QFont("Segoe UI", 10))
            cb.setMinimumHeight(48)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            ico_path = os.path.join(ROOT, a.icon)
            if os.path.exists(ico_path):
                cb.setIcon(QIcon(ico_path))
                cb.setIconSize(QSize(22, 22))
            self._checkboxes.append(cb)
            host_lay.addWidget(cb)

        host_lay.addStretch(1)
        scroll.setWidget(host)
        card_lay.addWidget(scroll, 1)

        # Opção extra
        extra_row = QHBoxLayout()
        extra_row.setSpacing(12)
        self.chk_iss = QCheckBox(" Após compilar, gerar também o instalador (Inno Setup)")
        self.chk_iss.setChecked(bool(self.state.get("run_iss", False)))
        self.chk_iss.setStyleSheet("QCheckBox { border: none; padding: 4px; }")
        extra_row.addWidget(self.chk_iss)
        extra_row.addStretch(1)
        card_lay.addLayout(extra_row)

        return card

    def _build_log_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(8)

        row = QHBoxLayout()
        row.addWidget(QLabel("Log:"))
        row.addStretch(1)
        btn_clear = QPushButton("Limpar log")
        btn_clear.setProperty("class", "Ghost")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_log)
        row.addWidget(btn_clear)
        lay.addLayout(row)

        self.log = QTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self.log, 1)

        # barra de progresso indeterminada
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)      # modo indeterminado
        self.progress.setVisible(False)
        self.progress.setFormat("Compilando…")
        lay.addWidget(self.progress)

        return card

    def _build_footer(self) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.lbl_status = QLabel("Pronto.")
        self.lbl_status.setObjectName("StatusLabel")
        row.addWidget(self.lbl_status)
        row.addStretch(1)

        self.btn_dist = QPushButton("Abrir dist/")
        self.btn_dist.setProperty("class", "Ghost")
        self.btn_dist.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dist.setEnabled(os.path.isdir(DIST_DIR))
        self.btn_dist.clicked.connect(lambda: self._open_folder(DIST_DIR))
        row.addWidget(self.btn_dist)

        self.btn_output = QPushButton("Abrir Output/")
        self.btn_output.setProperty("class", "Ghost")
        self.btn_output.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_output.setEnabled(os.path.isdir(OUTPUT_DIR))
        self.btn_output.clicked.connect(lambda: self._open_folder(OUTPUT_DIR))
        row.addWidget(self.btn_output)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setProperty("class", "Danger")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        row.addWidget(self.btn_cancel)

        self.btn_build = QPushButton("Compilar selecionados")
        self.btn_build.setProperty("class", "Primary")
        self.btn_build.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_build.clicked.connect(self._on_build)
        row.addWidget(self.btn_build)

        return w

    def _build_actions(self):
        act_build = QAction("Compilar", self)
        act_build.setShortcut(QKeySequence("Ctrl+B"))
        act_build.triggered.connect(self._on_build)
        self.addAction(act_build)

        act_clear = QAction("Limpar log", self)
        act_clear.setShortcut(QKeySequence("Ctrl+L"))
        act_clear.triggered.connect(self._clear_log)
        self.addAction(act_clear)

        act_quit = QAction("Sair", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        self.addAction(act_quit)

    # ---------------------------------------------------------------
    def _apply_saved_selection(self):
        saved: List[str] = self.state.get("apps", []) or []
        if not saved:
            # por default, marca todos
            saved = [a.key for a in APPS]
        for cb in self._checkboxes:
            cb.setChecked(cb.property("app_key") in saved)

    def _selected_keys(self) -> List[str]:
        return [cb.property("app_key") for cb in self._checkboxes if cb.isChecked()]

    def _set_all(self, value: bool):
        for cb in self._checkboxes:
            cb.setChecked(value)

    # ---------------------------------------------------------------
    def _append_log(self, text: str, color: Optional[str] = None):
        if color:
            html_text = text.replace("<", "&lt;").replace(">", "&gt;")
            self.log.append(f"<span style='color:{color}'>{html_text}</span>")
        else:
            self.log.append(text)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def _clear_log(self):
        self.log.clear()

    def _set_status(self, msg: str):
        self.lbl_status.setText(msg)
        self.statusBar().showMessage(msg)

    # ---------------------------------------------------------------
    def _on_build(self):
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, "Build em andamento",
                                    "Um build já está rodando. Cancele antes de iniciar outro.")
            return

        keys = self._selected_keys()
        if not keys:
            QMessageBox.warning(self, "Nenhum app selecionado",
                                "Marque pelo menos 1 app para compilar.")
            return

        if not os.path.isfile(SPEC_FILE):
            QMessageBox.critical(self, "Spec não encontrado",
                                 f"Não achei multi_apps.spec em:\n{SPEC_FILE}")
            return

        # Persiste seleção
        self.state["apps"] = keys
        self.state["run_iss"] = self.chk_iss.isChecked()
        save_state(self.state)

        # Limpa build/ e dist/FerramentasCompartilhadas/
        self._cleanup_previous()

        self._pending_iss = self.chk_iss.isChecked() and os.path.isfile(ISS_FILE)

        apps_value = "all" if len(keys) == len(APPS) else ",".join(keys)
        self._append_log(f"\n=== Iniciando build ===", color="#60A5FA")
        self._append_log(f"APPS_TO_BUILD={apps_value}")
        self._append_log(f"Spec: {SPEC_FILE}")
        self._append_log("")

        self._start_deps(apps_value, keys)

    def _cleanup_previous(self):
        for path in (os.path.join(ROOT, "build"), DIST_DIR):
            if os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    self._append_log(f"[aviso] não consegui remover {path}: {e}",
                                     color="#F59E0B")

    # ---------------------------------------------------------------
    def _start_deps(self, apps_value: str, keys: List[str]):
        """Instala o requirements de cada app selecionado antes do
        PyInstaller. Encadeia os pip installs em sequência; ao terminar,
        dispara o PyInstaller. SKIP_DEPS=1 pula a etapa."""
        if os.environ.get("SKIP_DEPS") == "1":
            self._append_log("[deps] SKIP_DEPS=1 -> pulando instalação de dependências.",
                             color="#F59E0B")
            self._start_pyinstaller(apps_value)
            return

        # pyinstaller é sempre necessário.
        queue: List[tuple] = [("pyinstaller", ["pyinstaller"])]

        # requirements files (apps web -> -web.txt), deduplicados na ordem.
        seen_files = set()
        for k in keys:
            f = APP_REQ_FILES.get(k)
            if not f or f in seen_files:
                continue
            seen_files.add(f)
            if not os.path.isfile(os.path.join(ROOT, f)):
                self._append_log(f"  [{k}] requirements ausente: {f}", color="#F87171")
                self._finish_build(success=False)
                return
            queue.append((k, ["-r", f]))

        # pacotes inline (apps sem arquivo), união preservando ordem.
        pkgs: List[str] = []
        for k in keys:
            for p in APP_REQ_PKGS.get(k, []):
                if p not in pkgs:
                    pkgs.append(p)
        if pkgs:
            queue.append(("pacotes", pkgs))

        self._dep_queue = queue
        self._dep_apps_value = apps_value
        self._stage = "deps"
        self._set_busy(True, "Instalando dependências…")
        self._append_log("\n=== Instalando dependências ===", color="#60A5FA")
        self._run_next_dep()

    def _run_next_dep(self):
        if not self._dep_queue:
            self._append_log("\n=== Dependências OK ===", color="#34D399")
            self._start_pyinstaller(self._dep_apps_value)
            return

        label, pip_args = self._dep_queue.pop(0)
        self._append_log(f"  [{label}] pip install {' '.join(pip_args)}")

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")

        proc = QProcess(self)
        proc.setProcessEnvironment(env)
        proc.setWorkingDirectory(ROOT)
        proc.setProgram(sys.executable)
        proc.setArguments(["-m", "pip", "install", *pip_args])
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_stdout)
        proc.finished.connect(self._on_dep_finished)
        proc.errorOccurred.connect(self._on_process_error)
        self._process = proc
        proc.start()

    def _on_dep_finished(self, code: int, status: QProcess.ExitStatus):
        if self._process is not None:
            self._process.deleteLater()
            self._process = None

        if status == QProcess.ExitStatus.CrashExit or code != 0:
            self._append_log(f"\n=== Instalação de dependências falhou (exit={code}) ===",
                             color="#F87171")
            self._append_log("    Corrija o ambiente ou use SKIP_DEPS=1 para pular.",
                             color="#F59E0B")
            self._finish_build(success=False)
            return

        self._run_next_dep()

    # ---------------------------------------------------------------
    def _start_pyinstaller(self, apps_value: str):
        self._stage = "pyinstaller"
        self._set_busy(True, "Rodando PyInstaller…")

        env = QProcessEnvironment.systemEnvironment()
        env.insert("APPS_TO_BUILD", apps_value)
        env.insert("PYTHONIOENCODING", "utf-8")

        proc = QProcess(self)
        proc.setProcessEnvironment(env)
        proc.setWorkingDirectory(ROOT)
        proc.setProgram(sys.executable)
        proc.setArguments(["-m", "PyInstaller", "--noconfirm", "--clean", SPEC_FILE])
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_stdout)
        proc.finished.connect(self._on_pyinstaller_finished)
        proc.errorOccurred.connect(self._on_process_error)
        self._process = proc
        proc.start()

    def _on_pyinstaller_finished(self, code: int, status: QProcess.ExitStatus):
        if self._process is not None:
            self._process.deleteLater()
            self._process = None

        if status == QProcess.ExitStatus.CrashExit or code != 0:
            self._append_log(f"\n=== PyInstaller falhou (exit={code}) ===",
                             color="#F87171")
            self._finish_build(success=False)
            return

        self._copy_app_configs()
        self._append_log("\n=== PyInstaller concluído ===", color="#34D399")

        if self._pending_iss:
            self._start_iscc()
        else:
            self._finish_build(success=True)

    def _copy_app_configs(self):
        src_dir = os.path.join(ROOT, "app_configs")
        if not os.path.isdir(src_dir) or not os.path.isdir(DIST_DIR):
            return
        copied = 0
        for name in os.listdir(src_dir):
            if not name.lower().endswith(".exe.config"):
                continue
            try:
                shutil.copy2(os.path.join(src_dir, name), os.path.join(DIST_DIR, name))
                copied += 1
            except Exception as e:
                self._append_log(f"[aviso] falha ao copiar {name}: {e}", color="#F59E0B")
        if copied:
            self._append_log(f"[fixup] configs .NET copiadas: {copied}")

    # ---------------------------------------------------------------
    def _start_iscc(self):
        iscc = self._find_iscc()
        if not iscc:
            self._append_log(
                "[aviso] ISCC.exe não encontrado no PATH nem em "
                "'C:\\Program Files (x86)\\Inno Setup 6\\'. Pulando o instalador.",
                color="#F59E0B")
            self._finish_build(success=True)
            return

        self._stage = "iscc"
        self._set_busy(True, "Gerando instalador (ISCC)…")

        args = []
        keys = self._selected_keys()
        if len(keys) == 1:
            args.append(f"/DAPP_ONLY={keys[0]}")
        args.append(ISS_FILE)

        self._append_log(f"\n=== Compilando instalador ===", color="#60A5FA")
        self._append_log(f"ISCC {' '.join(args)}")
        self._append_log("")

        proc = QProcess(self)
        proc.setWorkingDirectory(ROOT)
        proc.setProgram(iscc)
        proc.setArguments(args)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_stdout)
        proc.finished.connect(self._on_iscc_finished)
        proc.errorOccurred.connect(self._on_process_error)
        self._process = proc
        proc.start()

    def _on_iscc_finished(self, code: int, status: QProcess.ExitStatus):
        if self._process is not None:
            self._process.deleteLater()
            self._process = None

        if status == QProcess.ExitStatus.CrashExit or code != 0:
            self._append_log(f"\n=== ISCC falhou (exit={code}) ===",
                             color="#F87171")
            self._finish_build(success=False)
            return

        self._append_log("\n=== Instalador gerado ===", color="#34D399")
        self._finish_build(success=True)

    # ---------------------------------------------------------------
    def _find_iscc(self) -> Optional[str]:
        candidates = [
            shutil.which("ISCC.exe"),
            shutil.which("ISCC"),
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return None

    # ---------------------------------------------------------------
    def _on_stdout(self):
        if self._process is None:
            return
        raw = bytes(self._process.readAllStandardOutput())
        if not raw:
            return
        text = raw.decode("utf-8", errors="replace")
        # append preservando quebras de linha
        for line in text.replace("\r\n", "\n").split("\n"):
            if line:
                self._append_log(line)

    def _on_process_error(self, err: QProcess.ProcessError):
        self._append_log(f"[erro] process error: {int(err)}", color="#F87171")

    # ---------------------------------------------------------------
    def _on_cancel(self):
        if self._process is None:
            return
        ret = QMessageBox.question(
            self, "Cancelar build",
            "Tem certeza que deseja interromper o build em andamento?"
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        try:
            self._process.kill()
            self._append_log("\n=== Build cancelado pelo usuário ===",
                             color="#F59E0B")
        except Exception as e:
            self._append_log(f"[aviso] falha ao matar processo: {e}",
                             color="#F59E0B")

    # ---------------------------------------------------------------
    def _finish_build(self, success: bool):
        self._stage = "idle"
        self._pending_iss = False
        self._set_busy(False, "Concluído." if success else "Falhou.")
        self.btn_dist.setEnabled(os.path.isdir(DIST_DIR))
        self.btn_output.setEnabled(os.path.isdir(OUTPUT_DIR))

        if success:
            QMessageBox.information(
                self, "Build concluído",
                "Compilação concluída com sucesso."
            )
        # falhas já foram mostradas via log colorido

    def _set_busy(self, busy: bool, message: str):
        self.btn_build.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.progress.setVisible(busy)
        for cb in self._checkboxes:
            cb.setEnabled(not busy)
        self.chk_iss.setEnabled(not busy)
        self._set_status(message)

    # ---------------------------------------------------------------
    def _open_folder(self, path: str):
        if not os.path.isdir(path):
            QMessageBox.information(self, "Pasta inexistente",
                                    f"A pasta ainda não existe:\n{path}")
            return
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            import webbrowser
            webbrowser.open(path)

    # ---------------------------------------------------------------
    def closeEvent(self, ev):
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            ret = QMessageBox.question(
                self, "Build em andamento",
                "Um build está rodando. Fechar vai cancelá-lo. Deseja continuar?"
            )
            if ret != QMessageBox.StandardButton.Yes:
                ev.ignore()
                return
            try:
                self._process.kill()
            except Exception:
                pass

        try:
            self.state["apps"] = self._selected_keys()
            self.state["run_iss"] = self.chk_iss.isChecked()
            save_state(self.state)
        except Exception:
            pass
        super().closeEvent(ev)


# =====================================================================
# main
# =====================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)

    icn = os.path.join(ROOT, "apps", "launcher", "eng.ico")
    if os.path.exists(icn):
        app.setWindowIcon(QIcon(icn))

    win = BuildWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
