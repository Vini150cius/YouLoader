import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QLineEdit, QComboBox,
                               QPushButton, QFileDialog, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QStandardPaths, Signal, QObject
from PySide6.QtGui import QIcon, QPixmap
import yt_dlp
import os
import urllib.request
import zipfile

def baixar_ffmpeg(destino="ffmpeg"):
    ffmpeg_exe = os.path.join(destino, "bin", "ffmpeg.exe")
    if os.path.exists(ffmpeg_exe):
        return

    print("Baixando FFmpeg...")
    os.makedirs(destino, exist_ok=True)
    zip_path = os.path.join(destino, "ffmpeg.zip")

    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    urllib.request.urlretrieve(url, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(destino)

    os.remove(zip_path)

    for root, dirs, files in os.walk(destino):
        for d in dirs:
            if "bin" in d:
                src = os.path.join(root, d)
                dest_bin = os.path.join(destino, "bin")
                if not os.path.exists(dest_bin):
                    os.rename(src, dest_bin)
                break
        break

def configurar_ffmpeg():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    ffmpeg_path = os.path.join(base_path, "ffmpeg", "bin")
    os.environ["PATH"] += os.pathsep + ffmpeg_path

class DownloadProgress(QObject):
    progress_update = Signal(float, str)
    download_complete = Signal()
    download_error = Signal(str)

    def __init__(self):
        super().__init__()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%')
            p = p.replace('%', '').strip()
            try:
                percent = float(p)
            except ValueError:
                percent = 0

            speed = d.get('_speed_str', '')
            eta = d.get('_eta_str', '')
            info = f"Velocidade: {speed} | Tempo restante: {eta}"

            self.progress_update.emit(percent, info)

        elif d['status'] == 'finished':
            self.download_complete.emit()

        elif d['status'] == 'error':
            self.download_error.emit(str(d.get('error', 'Erro desconhecido')))


class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.setFixedSize(500, 400)

        self.default_download_folder = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)

        self.setup_icon()
        self.logo_pixmap = QPixmap("youtube-logo.png")

        self.progress_manager = DownloadProgress()
        self.progress_manager.progress_update.connect(self.update_progress)
        self.progress_manager.download_complete.connect(self.download_finished)
        self.progress_manager.download_error.connect(self.download_error)

        self.init_ui()

    def setup_icon(self):
        self.setWindowIcon(QIcon("youtube-icon.png"))

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        logo_layout = QHBoxLayout()

        logo_label = QLabel()
        logo_label.setPixmap(self.logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)

        app_name = QLabel("YouTube Downloader")
        app_name.setStyleSheet("font-size: 16pt; font-weight: bold; color: #FF0000;")
        app_name.setAlignment(Qt.AlignCenter)

        logo_layout.addStretch()
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(app_name)
        logo_layout.addStretch()
        logo_label.setFixedSize(110, 64)
        logo_label.setScaledContents(True)

        main_layout.addLayout(logo_layout)
        main_layout.addSpacing(10)

        url_label = QLabel("Link do vídeo do YouTube:")
        self.url_input = QLineEdit()
        main_layout.addWidget(url_label)
        main_layout.addWidget(self.url_input)

        quality_label = QLabel("Qualidade do vídeo:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Alta", "Média", "Baixa"])
        main_layout.addWidget(quality_label)
        main_layout.addWidget(self.quality_combo)

        format_label = QLabel("Formato:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mp3"])
        main_layout.addWidget(format_label)
        main_layout.addWidget(self.format_combo)

        folder_label = QLabel("Pasta de destino:")
        main_layout.addWidget(folder_label)

        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setText(self.default_download_folder)
        self.folder_btn = QPushButton("Selecionar")
        self.folder_btn.clicked.connect(self.choose_folder)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.folder_btn)
        main_layout.addLayout(folder_layout)

        self.download_btn = QPushButton("Baixar")
        self.download_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.download_btn.clicked.connect(self.download)
        main_layout.addWidget(self.download_btn, alignment=Qt.AlignCenter)

        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #FF0000;
                width: 10px;
                margin: 0.5px;
            }
        """)

        self.status_label = QLabel("Pronto para download")
        self.status_label.setAlignment(Qt.AlignCenter)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)

        main_layout.addLayout(progress_layout)

        main_layout.addStretch()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Destino", self.default_download_folder)
        if folder:
            self.folder_input.setText(folder)

    def download(self):
        url = self.url_input.text().strip()
        quality = self.quality_combo.currentText()
        format_type = self.format_combo.currentText()
        folder = self.folder_input.text().strip()

        if not url:
            QMessageBox.warning(self, "Aviso", "Insira o link do vídeo.")
            return

        if not folder:
            folder = self.default_download_folder

        if format_type == "mp4":
            if quality == "Alta":
                format_yt = "bestvideo+bestaudio"
            elif quality == "Média":
                format_yt = "best[height<=480]"
            else:
                format_yt = "worst"
            ext = "mp4"
        else:
            format_yt = "bestaudio"
            ext = "mp3"

        ydl_opts = {
            'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
            'format': format_yt,
            'progress_hooks': [self.progress_manager.progress_hook],
        }

        if format_type == "mp3":
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })

        self.progress_bar.setValue(0)
        self.status_label.setText("Iniciando download...")
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Baixando...")

        from threading import Thread

        def download_thread():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                self.progress_manager.download_error.emit(str(e))

        Thread(target=download_thread, daemon=True).start()

    def update_progress(self, percent, info):
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(info)

    def download_finished(self):
        self.progress_bar.setValue(100)
        self.status_label.setText("Download concluído com sucesso!")
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Baixar")
        QMessageBox.information(self, "Sucesso",
                                f"Download concluído em:\n{self.folder_input.text() or self.default_download_folder}")

    def download_error(self, error_msg):
        self.progress_bar.setValue(0)
        self.status_label.setText("Erro no download")
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Baixar")
        QMessageBox.critical(self, "Erro", f"Erro ao baixar vídeo:\n{error_msg}")


def main():
    baixar_ffmpeg()
    configurar_ffmpeg()
    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()