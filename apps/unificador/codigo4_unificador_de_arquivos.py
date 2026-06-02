import sys
import os
import csv
import re
import traceback
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

import importlib

try:
    chardet = importlib.import_module("chardet")
except Exception as exc:  # pragma: no cover - defensive
    raise SystemExit("Dependencia ausente: chardet. Instale com: pip install chardet") from exc

try:
    import polars as pl
except Exception as exc:  # pragma: no cover - defensive
    raise SystemExit("Dependencia ausente: polars. Instale com: pip install polars") from exc

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    QAbstractItemView = QtWidgets.QAbstractItemView
except Exception as exc:  # pragma: no cover - defensive
    raise SystemExit("Dependencia ausente: PySide6. Instale com: pip install PySide6") from exc

try:
    import qtawesome as qta
except Exception:
    qta = None


LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "unificador_debug.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def _log_debug(message: str):
    logging.debug(message)


def _log_exception(context: str, exc: Exception):
    logging.error("%s | %s\n%s", context, exc, traceback.format_exc())


def detect_encoding(file_path: str) -> str:
    """Detecta a codificacao de um arquivo; se nao detectar, usa 'utf-8'."""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    enc = (result.get('encoding') or 'utf-8').lower()
    if enc in ('ascii', 'us-ascii', 'ansi_x3.4-1968'):
        return 'utf-8'
    return enc


def detect_separator(file_path: str, encoding: str) -> str:
    """
    Detecta o separador mais provavel; faz fallback para candidatos comuns.
    O csv.Sniffer.sniff aceita apenas str|None para 'delimiters', entao usamos
    uma string com todos os candidatos.
    """
    sample = ""
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            sample = f.read(4096)
            if not sample:
                return ','
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|:')
            return dialect.delimiter
    except Exception:
        candidates = [',', ';', '\t', '|', ':']
        counts = {d: sample.count(d) for d in candidates} if sample else {d: 0 for d in candidates}
    return max(counts, key=lambda d: counts.get(d, 0)) if any(counts.values()) else ','


def _ensure_str_columns(df: pl.DataFrame) -> pl.DataFrame:
    _log_debug(f"_ensure_str_columns | columns={df.columns}")
    new_names: List[str] = []
    counts: Dict[str, int] = {}
    for col in df.columns:
        name = str(col)
        if name in counts:
            counts[name] += 1
            name = f"{name}_{counts[name]}"
        else:
            counts[name] = 0
        new_names.append(name)
    if new_names == df.columns:
        return df
    return df.rename(dict(zip(df.columns, new_names)))


def _read_csv_polars(file_path: str) -> pl.DataFrame:
    encoding = detect_encoding(file_path)
    sep = detect_separator(file_path, encoding)
    _log_debug(f"_read_csv_polars | file={file_path} | encoding={encoding} | sep={sep}")
    df = pl.read_csv(
        file_path,
        encoding=encoding,
        separator=sep,
        ignore_errors=True,
        infer_schema_length=1000,
    )
    df = _ensure_str_columns(df)
    out = df.with_columns(pl.all().cast(pl.Utf8))
    _log_debug(f"_read_csv_polars | columns={out.columns} | dtypes={out.dtypes}")
    return out


def _read_excel_polars(file_path: str) -> pl.DataFrame:
    try:
        df = pl.read_excel(file_path)
        df = _ensure_str_columns(df)
        out = df.with_columns(pl.all().cast(pl.Utf8))
        _log_debug(f"_read_excel_polars(polars) | file={file_path} | columns={out.columns} | dtypes={out.dtypes}")
        return out
    except Exception:
        try:
            pandas = importlib.import_module("pandas")
        except Exception as exc:
            raise SystemExit(
                "Dependencia ausente: pandas (ou fastexcel). Instale com: pip install pandas openpyxl"
            ) from exc
        pdf = pandas.read_excel(file_path, engine="openpyxl")
        pdf.columns = [str(c) for c in pdf.columns]
        try:
            out = pl.from_pandas(pdf).with_columns(pl.all().cast(pl.Utf8))
            _log_debug(f"_read_excel_polars(pandas) | file={file_path} | columns={out.columns} | dtypes={out.dtypes}")
            return out
        except Exception as exc:
            if "pyarrow" not in str(exc).lower():
                raise
            data = {
                col: pdf[col].astype("string").fillna("").tolist()
                for col in pdf.columns
            }
            df = pl.DataFrame(data)
            df = _ensure_str_columns(df)
            out = df.with_columns(pl.all().cast(pl.Utf8))
            _log_debug(f"_read_excel_polars(pandas+fallback) | file={file_path} | columns={out.columns} | dtypes={out.dtypes}")
            return out


def try_read_file(file_path: str) -> pl.DataFrame:
    """
    Le CSV/TXT/XLSX tratando todas as colunas como texto (Utf8).
    Detecta codificacao e separador para CSV/TXT.
    """
    _log_debug(f"try_read_file | file={file_path}")
    lower = file_path.lower()
    if lower.endswith(('.csv', '.txt')):
        return _read_csv_polars(file_path)
    if lower.endswith('.xlsx'):
        return _read_excel_polars(file_path)
    raise ValueError(f"Tipo de arquivo nao suportado: {file_path}")


def read_file_columns(file_path: str) -> List[str]:
    _log_debug(f"read_file_columns | file={file_path}")
    lower = file_path.lower()
    if lower.endswith(('.csv', '.txt')):
        encoding = detect_encoding(file_path)
        sep = detect_separator(file_path, encoding)
        df = pl.read_csv(
            file_path,
            encoding=encoding,
            separator=sep,
            n_rows=0,
            ignore_errors=True,
        )
        return [str(c) for c in df.columns]
    if lower.endswith('.xlsx'):
        try:
            df = pl.read_excel(file_path)
            return [str(c) for c in df.columns]
        except Exception:
            try:
                pandas = importlib.import_module("pandas")
            except Exception as exc:
                raise SystemExit(
                    "Dependencia ausente: pandas (ou fastexcel). Instale com: pip install pandas openpyxl"
                ) from exc
            pdf = pandas.read_excel(file_path, engine="openpyxl", nrows=0)
            return [str(c) for c in pdf.columns]
    raise ValueError(f"Tipo de arquivo nao suportado: {file_path}")


def normalize_column_name(name: str) -> str:
    cleaned = re.sub(r'[^a-z0-9]+', '', name.strip().lower())
    return cleaned


@dataclass
class ColumnMappingResult:
    mapping: Dict[str, str]
    ordered_targets: List[str]


class ColumnMappingDialog(QtWidgets.QDialog):
    def __init__(self, columns: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mapeamento de Colunas")
        self.setModal(True)
        self._columns = columns
        self._result: ColumnMappingResult | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        info = QtWidgets.QLabel(
            "Foram encontradas colunas diferentes entre os arquivos. "
            "Escolha quais manter e renomeie se necessario."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Coluna", "Manter", "Renomear para"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        for col in self._columns:
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_col = QtWidgets.QTableWidgetItem(col)
            self.table.setItem(row, 0, item_col)

            item_keep = QtWidgets.QTableWidgetItem()
            item_keep.setCheckState(QtCore.Qt.CheckState.Checked)
            item_keep.setFlags(item_keep.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            self.table.setItem(row, 1, item_keep)

            editor = QtWidgets.QLineEdit(col)
            editor.setStyleSheet("color: #f8fafc;")
            self.table.setCellWidget(row, 2, editor)

        btn_bar = QtWidgets.QHBoxLayout()
        btn_auto = QtWidgets.QPushButton("Auto-merge similares")
        btn_auto.clicked.connect(self._auto_merge)
        btn_bar.addWidget(btn_auto)
        btn_bar.addStretch(1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(btn_bar)
        layout.addWidget(buttons)

    def _auto_merge(self):
        groups: Dict[str, List[int]] = {}
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue
            name = item.text()
            key = normalize_column_name(name)
            groups.setdefault(key, []).append(row)

        for rows in groups.values():
            if len(rows) <= 1:
                continue
            base_item = self.table.item(rows[0], 0)
            if base_item is None:
                continue
            base_name = base_item.text()
            for row in rows:
                editor = self.table.cellWidget(row, 2)
                if isinstance(editor, QtWidgets.QLineEdit):
                    editor.setText(base_name)

    def _accept(self):
        mapping: Dict[str, str] = {}
        ordered_targets: List[str] = []

        for row in range(self.table.rowCount()):
            col_item = self.table.item(row, 0)
            if col_item is None:
                continue
            col_name = col_item.text()
            keep_item = self.table.item(row, 1)
            keep = keep_item.checkState() == QtCore.Qt.CheckState.Checked if keep_item else False
            editor = self.table.cellWidget(row, 2)
            new_name = col_name
            if isinstance(editor, QtWidgets.QLineEdit) and editor.text().strip():
                new_name = editor.text().strip()

            if keep:
                mapping[col_name] = new_name
                if new_name not in ordered_targets:
                    ordered_targets.append(new_name)

        if not mapping:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione pelo menos uma coluna.")
            return

        self._result = ColumnMappingResult(mapping=mapping, ordered_targets=ordered_targets)
        self.accept()

    def result_mapping(self) -> ColumnMappingResult | None:
        return self._result


class DropArea(QtWidgets.QFrame):
    filesDropped = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DropArea")
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("Arraste e solte arquivos aqui")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("DropLabel")
        layout.addWidget(label)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        urls = event.mimeData().urls()
        files = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if files:
            self.filesDropped.emit(files)


class MergeWorker(QtCore.QObject):
    progress = QtCore.Signal(int, str)
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)

    def __init__(self, files: List[str], save_path: str, mapping: ColumnMappingResult):
        super().__init__()
        self.files = files
        self.save_path = save_path
        self.mapping = mapping

    def _apply_mapping(self, df: pl.DataFrame) -> pl.DataFrame:
        _log_debug(f"_apply_mapping | df.columns={df.columns} | mapping={self.mapping.mapping}")
        target_to_sources: Dict[str, List[str]] = {}
        for src, target in self.mapping.mapping.items():
            target_to_sources.setdefault(target, []).append(src)

        exprs = []
        for target in self.mapping.ordered_targets:
            sources = target_to_sources.get(target, [])
            cols = [c for c in sources if c in df.columns]
            if not cols:
                exprs.append(pl.lit(None).alias(target))
            elif len(cols) == 1:
                exprs.append(pl.col(cols[0]).alias(target))
            else:
                exprs.append(pl.coalesce([pl.col(c) for c in cols]).alias(target))
        return df.select(exprs)

    def run(self):
        try:
            _log_debug(f"MergeWorker.run | files={self.files} | save={self.save_path}")
            dataframes: List[pl.DataFrame] = []
            total = len(self.files)
            for idx, file_path in enumerate(self.files, start=1):
                df = try_read_file(file_path)
                df = self._apply_mapping(df)
                dataframes.append(df)
                self.progress.emit(idx, file_path)

            if not dataframes:
                self.failed.emit("Nenhum dado foi carregado.")
                return

            merged = pl.concat(dataframes, how="vertical")

            try:
                merged.write_excel(self.save_path)
            except Exception:
                merged.to_pandas().to_excel(self.save_path, index=False)

            self.finished.emit(self.save_path)
        except Exception as exc:
            _log_exception("MergeWorker.run failed", exc)
            self.failed.emit(str(exc))


class FileMergerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mesclador de Arquivos - Converter para XLSX")
        self.resize(860, 520)
        self.files: List[str] = []
        self._thread: QtCore.QThread | None = None
        self._worker: MergeWorker | None = None
        self.setup_ui()

    def setup_ui(self):
        layout_principal = QtWidgets.QVBoxLayout(self)

        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self.add_files)
        layout_principal.addWidget(self.drop_area)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Arquivo", "Tamanho (MB)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(240)
        self.table.setAlternatingRowColors(True)
        layout_principal.addWidget(self.table)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        layout_principal.addWidget(self.progress)

        layout_botoes = QtWidgets.QHBoxLayout()

        self.btn_selecionar = QtWidgets.QPushButton("Selecionar Arquivos")
        self._set_button_icon(self.btn_selecionar, "fa.folder-open", QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon)
        self.btn_selecionar.clicked.connect(self.select_files)
        layout_botoes.addWidget(self.btn_selecionar)

        self.btn_mesclar = QtWidgets.QPushButton("Mesclar Arquivos para XLSX")
        self._set_button_icon(self.btn_mesclar, "fa.compress", QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton)
        self.btn_mesclar.clicked.connect(self.merge_files)
        layout_botoes.addWidget(self.btn_mesclar)

        self.btn_sair = QtWidgets.QPushButton("Sair")
        self._set_button_icon(self.btn_sair, "fa.sign-out", QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton)
        self.btn_sair.clicked.connect(self.close)
        layout_botoes.addWidget(self.btn_sair)

        layout_principal.addLayout(layout_botoes)

    def add_files(self, files: List[str]):
        for file_path in files:
            if file_path and file_path not in self.files:
                self.files.append(file_path)
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        for file_path in self.files:
            row = self.table.rowCount()
            self.table.insertRow(row)

            item_name = QtWidgets.QTableWidgetItem(os.path.basename(file_path))
            item_name.setToolTip(file_path)
            self.table.setItem(row, 0, item_name)

            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            item_size = QtWidgets.QTableWidgetItem(f"{size_mb:.2f}")
            item_size.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 1, item_size)

            item_status = QtWidgets.QTableWidgetItem("Pendente")
            self.table.setItem(row, 2, item_status)

    def select_files(self):
        filtros = (
            "Arquivos CSV (*.csv);;"
            "Arquivos de Texto (*.txt);;"
            "Arquivos do Excel (*.xlsx);;"
            "Todos os Arquivos (*)"
        )
        arquivos, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Selecionar Arquivos", "", filtros)
        if arquivos:
            self.add_files(arquivos)

    def _collect_columns(self, files: List[str]) -> List[str]:
        columns = []
        seen = set()
        for file_path in files:
            cols = read_file_columns(file_path)
            for col in cols:
                if col not in seen:
                    seen.add(col)
                    columns.append(col)
        return columns

    def _all_same_columns(self, files: List[str]) -> Tuple[bool, List[str]]:
        base_cols: List[str] | None = None
        for file_path in files:
            cols = read_file_columns(file_path)
            if base_cols is None:
                base_cols = cols
            elif cols != base_cols:
                return False, base_cols or []
        return True, base_cols or []

    def merge_files(self):
        if not self.files:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum arquivo selecionado!")
            return

        try:
            all_same, base_cols = self._all_same_columns(self.files)
            _log_debug(f"merge_files | all_same={all_same} | base_cols={base_cols}")
            if all_same and base_cols:
                mapping_result = ColumnMappingResult(
                    mapping={c: c for c in base_cols},
                    ordered_targets=base_cols,
                )
            else:
                columns = self._collect_columns(self.files)
                _log_debug(f"merge_files | collected_columns={columns}")
                dialog = ColumnMappingDialog(columns, self)
                if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return
                mapping_result = dialog.result_mapping()
                if not mapping_result:
                    return
        except Exception as exc:
            _log_exception("merge_files failed while reading columns", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao ler colunas: {exc}")
            return

        caminho_salvar, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Salvar Arquivo Mesclado",
            "",
            "Arquivos do Excel (*.xlsx)"
        )
        if not caminho_salvar:
            return
        if not caminho_salvar.lower().endswith('.xlsx'):
            caminho_salvar += '.xlsx'

        _log_debug(f"merge_files | output={caminho_salvar}")
        self._set_busy(True)
        self.progress.setMaximum(len(self.files))
        self.progress.setValue(0)
        self.progress.setFormat("%v/%m")

        thread = QtCore.QThread(self)
        worker = MergeWorker(self.files, caminho_salvar, mapping_result)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_progress(self, value: int, filename: str):
        self.progress.setValue(value)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.toolTip() == filename:
                status_item = self.table.item(row, 2)
                if status_item is not None:
                    status_item.setText("Processado")
                break

    def _on_finished(self, save_path: str):
        self._set_busy(False)
        QtWidgets.QMessageBox.information(
            self,
            "Sucesso",
            f"Arquivos mesclados e salvos em:\n{save_path}!"
        )

    def _on_failed(self, message: str):
        self._set_busy(False)
        QtWidgets.QMessageBox.critical(self, "Erro", message)

    def _set_busy(self, busy: bool):
        self.btn_selecionar.setEnabled(not busy)
        self.btn_mesclar.setEnabled(not busy)
        self.drop_area.setEnabled(not busy)

    def _set_button_icon(self, button: QtWidgets.QPushButton, icon_name: str, fallback: QtWidgets.QStyle.StandardPixmap):
        if qta is not None:
            try:
                button.setIcon(qta.icon(icon_name, color="#e5e7eb"))
                return
            except Exception:
                pass
        else:
            pass
        button.setIcon(self.style().standardIcon(fallback))


def apply_modern_theme(app: QtWidgets.QApplication):
    qss = """
        QWidget {
            background: #0b0f14;
            color: #e5e7eb;
            font-size: 12px;
        }
        QPushButton {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 10px;
            padding: 8px 14px;
        }
        QPushButton:hover { background: #1f2937; }
        QPushButton:pressed { background: #0f172a; }
        QProgressBar {
            border: 1px solid #1f2937;
            border-radius: 8px;
            text-align: center;
            background: #0f172a;
            padding: 2px;
        }
        QProgressBar::chunk {
            background: #2563eb;
            border-radius: 6px;
        }
        QTableWidget {
            background-color: #0f172a;   /* Fundo escuro */
            color: #f8fafc;              /* Texto quase branco para alto contraste */
            gridline-color: #1f2937;
            selection-background-color: #2563eb; /* Cor azul ao selecionar */
            selection-color: #ffffff;    /* Texto branco na seleção */
            border: 1px solid #1f2937;
            border-radius: 10px;
        }

        QTableWidget::item {
            padding: 6px 10px;
            color: #f8fafc;              /* Garante que o texto de cada item seja visivel */
        }

        /* Garante contraste nos cabecalhos */
        QHeaderView::section {
            background-color: #111827;
            color: #9ca3af;
            border: none;
            padding: 6px;
            font-weight: bold;
        }
        #DropArea {
            border: 2px dashed #1f2937;
            border-radius: 12px;
            padding: 14px;
            background: #0f172a;
        }
        #DropLabel {
            color: #9ca3af;
            font-size: 13px;
        }
    """
    try:
        qt_material = importlib.import_module("qt_material")
        qt_material.apply_stylesheet(app, theme='dark_teal.xml', extra=qss)
    except Exception:
        app.setStyleSheet(qss)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    apply_modern_theme(app)
    janela = FileMergerApp()
    janela.show()
    sys.exit(app.exec())
