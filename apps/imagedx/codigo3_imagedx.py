import sys
import os
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QBrush, QColor
from PIL import Image, ImageGrab

# --- Compatibilidade Pillow (todas as versões) -------------------------------
# Define uma constante RESAMPLE_LANCZOS independente da versão do Pillow
try:
    # Pillow >= 9.1 expõe o enum Resampling
    from PIL.Image import Resampling as _Resampling  # type: ignore[attr-defined]
    RESAMPLE_LANCZOS = _Resampling.LANCZOS
except Exception:
    # Pillow antigo: usa a constante no módulo Image; se não existir, cai para BICUBIC
    RESAMPLE_LANCZOS = getattr(Image, "LANCZOS", Image.BICUBIC)
# ----------------------------------------------------------------------------

class ImageResizerApp(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Resizer")
        self.images = []             # Lista para armazenar as imagens inseridas
        self.legend_image = None     # Imagem da legenda (se inserida)
        self.combined_image = None   # Imagem combinada final

        # Layout principal em grade
        grid = QtWidgets.QGridLayout(self)

        # Linha 0: Largura (cm)
        lbl_width = QtWidgets.QLabel("Largura (cm):")
        grid.addWidget(lbl_width, 0, 0)
        self.width_entry = QtWidgets.QLineEdit()
        grid.addWidget(self.width_entry, 0, 1)

        # Linha 1: Altura (cm)
        lbl_height = QtWidgets.QLabel("Altura (cm):")
        grid.addWidget(lbl_height, 1, 0)
        self.height_entry = QtWidgets.QLineEdit()
        grid.addWidget(self.height_entry, 1, 1)

        # Linha 2: Espaçamento entre as imagens (cm)
        lbl_spacing = QtWidgets.QLabel("Espaçamento entre as imagens (cm):")
        grid.addWidget(lbl_spacing, 2, 0)
        self.spacing_entry = QtWidgets.QLineEdit()
        grid.addWidget(self.spacing_entry, 2, 1)

        # Linha 3: Caminho da Pasta e botão para escolher pasta
        lbl_path = QtWidgets.QLabel("Caminho da Pasta:")
        grid.addWidget(lbl_path, 3, 0)
        self.path_entry = QtWidgets.QLineEdit()
        grid.addWidget(self.path_entry, 3, 1)
        btn_select_folder = QtWidgets.QPushButton("Escolher Pasta")
        btn_select_folder.clicked.connect(self.select_folder)
        grid.addWidget(btn_select_folder, 3, 2)

        # Linha 4: Nome do Arquivo
        lbl_filename = QtWidgets.QLabel("Nome do Arquivo:")
        grid.addWidget(lbl_filename, 4, 0)
        self.file_name = QtWidgets.QLineEdit()
        grid.addWidget(self.file_name, 4, 1)

        # Linha 5: Botão para inserir imagem de legenda e seleção de posição
        btn_insert_legend = QtWidgets.QPushButton("Inserir Imagem de Legenda")
        btn_insert_legend.clicked.connect(self.insert_legend_image)
        grid.addWidget(btn_insert_legend, 5, 0)
        lbl_position = QtWidgets.QLabel("Posição da Legenda:")
        grid.addWidget(lbl_position, 5, 1)
        self.legend_position = QtWidgets.QComboBox()
        positions = ["Inferior Direito", "Inferior Esquerdo", "Superior Direito", "Superior Esquerdo"]
        self.legend_position.addItems(positions)
        index = self.legend_position.findText("Inferior Esquerdo", Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.legend_position.setCurrentIndex(index)
        grid.addWidget(self.legend_position, 5, 2)

        # Linha 6: Botões para inserir imagens (Topologia, Nível de Tensão, Carregamento)
        btn_topologia = QtWidgets.QPushButton("Topologia")
        btn_topologia.clicked.connect(lambda: self.insert_image(0))
        grid.addWidget(btn_topologia, 6, 0)
        btn_tensao = QtWidgets.QPushButton("Nível de Tensão")
        btn_tensao.clicked.connect(lambda: self.insert_image(1))
        grid.addWidget(btn_tensao, 6, 1)
        btn_carregamento = QtWidgets.QPushButton("Carregamento")
        btn_carregamento.clicked.connect(lambda: self.insert_image(2))
        grid.addWidget(btn_carregamento, 6, 2)

        # Linha 7: Botão para exibir as imagens redimensionadas
        btn_display = QtWidgets.QPushButton("Exibir Imagens Redimensionadas")
        btn_display.clicked.connect(self.display_images)
        grid.addWidget(btn_display, 7, 0, 1, 3)

        # Linha 8: Botão para salvar a imagem combinada
        btn_save = QtWidgets.QPushButton("Salvar Imagem Combinada")
        btn_save.clicked.connect(self.save_combined_image)
        grid.addWidget(btn_save, 8, 0, 1, 3)

        # Linha 9: Área para visualização (usando QGraphicsView como canvas)
        self.scene = QtWidgets.QGraphicsScene()
        self.canvas = QtWidgets.QGraphicsView(self.scene)
        self.canvas.setBackgroundBrush(QBrush(QColor("white")))
        grid.addWidget(self.canvas, 9, 0, 1, 3)

    def cm_to_pixels(self, cm: float) -> int:
        """Converte centímetros para pixels (assumindo 96 DPI)."""
        return int((cm * 96) / 2.54)

    def pil2pixmap(self, im: Image.Image) -> QPixmap:
        """Converte uma imagem PIL para QPixmap."""
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        data = im.tobytes("raw", "RGBA")
        bytes_per_line = im.width * 4  # RGBA = 4 bytes/pixel
        qimage = QImage(data, im.width, im.height, bytes_per_line, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def insert_image(self, index: int) -> None:
        """
        Captura a imagem da área de transferência e a insere
        na posição indicada (substituindo se já existir).
        """
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            if len(self.images) > index:
                self.images[index] = img
            else:
                while len(self.images) < index:
                    self.images.append(None)
                self.images.append(img)
            QtWidgets.QMessageBox.information(self, "Imagem Inserida", f"Imagem {index + 1} inserida com sucesso!")
        else:
            QtWidgets.QMessageBox.warning(self, "Erro", "Nenhuma imagem encontrada na área de transferência.")

    def insert_legend_image(self) -> None:
        """Captura a imagem da área de transferência para usar como legenda."""
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            self.legend_image = img
            QtWidgets.QMessageBox.information(self, "Imagem de Legenda Inserida", "Imagem de legenda inserida com sucesso!")
        else:
            QtWidgets.QMessageBox.warning(self, "Erro", "Nenhuma imagem de legenda encontrada na área de transferência.")

    def display_images(self) -> None:
        """
        Redimensiona as imagens inseridas conforme os valores em centímetros,
        monta a imagem combinada e exibe cada imagem (lado a lado) na área de visualização.
        """
        try:
            width_cm = float(self.width_entry.text().replace(',', '.'))
            height_cm = float(self.height_entry.text().replace(',', '.'))
            spacing_cm = float(self.spacing_entry.text().replace(',', '.'))
        except ValueError:
            QtWidgets.QMessageBox.critical(self, "Erro", "Por favor, insira valores válidos para largura, altura e espaçamento.")
            return

        width_px = self.cm_to_pixels(width_cm)
        height_px = self.cm_to_pixels(height_cm)
        spacing_px = self.cm_to_pixels(spacing_cm)

        valid_images = [img for img in self.images if isinstance(img, Image.Image)]
        num_images = len(valid_images)
        if num_images == 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhuma imagem inserida para redimensionar.")
            return

        combined_width = (width_px * num_images) + (spacing_px * (num_images - 1))
        combined_height = height_px

        # Cria a imagem combinada (fundo branco)
        self.combined_image = Image.new("RGB", (combined_width, combined_height), "white")

        # Limpa a cena para atualizar a visualização
        self.scene.clear()

        x_offset = 0
        for img in valid_images:
            # Redimensiona a imagem com filtro LANCZOS compatível
            resized_img = img.resize((width_px, height_px), resample=RESAMPLE_LANCZOS)
            self.combined_image.paste(resized_img, (x_offset, 0))
            # Converte para QPixmap e adiciona na cena
            pixmap = self.pil2pixmap(resized_img)
            item = self.scene.addPixmap(pixmap)
            item.setPos(x_offset, 0)
            x_offset += width_px + spacing_px

        # Se houver imagem de legenda, redimensiona e insere na imagem combinada
        if self.legend_image:
            legend_width_px = int(0.279 * width_px)
            legend_height_px = int(0.218 * height_px)
            resized_legend = self.legend_image.resize((legend_width_px, legend_height_px), resample=RESAMPLE_LANCZOS)

            pos_text = self.legend_position.currentText()
            if pos_text == "Inferior Direito":
                position = (width_px - legend_width_px - 10, height_px - legend_height_px - 10)
            elif pos_text == "Inferior Esquerdo":
                position = (10, height_px - legend_height_px - 10)
            elif pos_text == "Superior Direito":
                position = (width_px - legend_width_px - 10, 10)
            elif pos_text == "Superior Esquerdo":
                position = (10, 10)
            else:
                position = (10, height_px - legend_height_px - 10)

            # Usa máscara se a legenda tiver alpha, preservando transparência
            mask = resized_legend.split()[-1] if resized_legend.mode == "RGBA" else None
            self.combined_image.paste(resized_legend, position, mask)

    def select_folder(self) -> None:
        """Abre um diálogo para seleção de pasta e atualiza o campo de caminho."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Selecione a Pasta")
        if folder:
            self.path_entry.setText(folder)

    def save_combined_image(self) -> None:
        """
        Salva a imagem combinada (se existente) no caminho e com o nome especificados.
        """
        if self.combined_image:
            folder = self.path_entry.text()
            filename = self.file_name.text()
            if not folder:
                QtWidgets.QMessageBox.critical(self, "Erro", "Por favor, selecione uma pasta para salvar o arquivo.")
                return
            if not filename:
                QtWidgets.QMessageBox.critical(self, "Erro", "Por favor, insira um nome para o arquivo.")
                return

            file_path = os.path.join(folder, f"{filename}.png")
            try:
                self.combined_image.save(file_path)
                QtWidgets.QMessageBox.information(self, "Imagem Salva", f"A imagem foi salva com sucesso em:\n{file_path}")
                self.file_name.clear()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar a imagem: {e}")
        else:
            QtWidgets.QMessageBox.warning(self, "Erro", "Nenhuma imagem combinada para salvar. Clique em 'Exibir Imagens Redimensionadas' primeiro.")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ImageResizerApp()
    window.show()
    sys.exit(app.exec())
