import sys
import os
import re
import traceback
import urllib.request
import zipfile
import logging
import subprocess
from threading import Thread
from datetime import datetime

log_dir = os.path.join(os.path.expanduser("~"), "YouLoader_logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def log_uncaught_exceptions(exctype, value, tb):
    logging.critical("Erro não capturado:", exc_info=(exctype, value, tb))
    traceback.print_exception(exctype, value, tb)
    with open(log_file, "a") as f:
        f.write("\n" + "=" * 50 + "\n")
        f.write(f"ERRO FATAL: {exctype.__name__}: {value}\n")
        f.write("=" * 50 + "\n")
        traceback.print_exception(exctype, value, tb, file=f)

    from PySide6.QtWidgets import QMessageBox, QApplication
    if QApplication.instance():
        QMessageBox.critical(None, "Erro Fatal",
                             f"Um erro fatal ocorreu ao iniciar o aplicativo.\n"
                             f"Detalhes do erro foram salvos em:\n{log_file}")

    sys.exit(1)


sys.excepthook = log_uncaught_exceptions

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                   QHBoxLayout, QLabel, QLineEdit, QComboBox,
                                   QPushButton, QFileDialog, QMessageBox, QProgressBar,
                                   QFrame)
    from PySide6.QtCore import Qt, QStandardPaths, Signal, QObject, QUrl
    from PySide6.QtGui import QIcon, QPixmap, QDesktopServices
    import yt_dlp
except ImportError as e:
    logging.critical(f"Erro ao importar módulos: {e}")
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro de Importação",
                             f"Falha ao importar módulos necessários: {e}\nVerifique o log em: {log_file}")
    except Exception:
        pass
    sys.exit(1)


# Regex simples para validar links do YouTube (vídeo, shorts ou youtu.be)
YOUTUBE_URL_RE = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w\-]+',
    re.IGNORECASE
)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    result = os.path.join(base_path, relative_path)
    logging.debug(f"Resource path para '{relative_path}': {result}")
    return result


def verificar_ffmpeg():
    try:
        import shutil

        # Primeiro tenta encontrar o FFmpeg no PATH do sistema
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            logging.info(f"FFmpeg encontrado no sistema em: {ffmpeg_path}")
            return True

        # Se não encontrou no PATH, tenta executar diretamente (sem shell=True,
        # que é desnecessário aqui e mascara o erro real caso o binário não exista)
        result = subprocess.run(["ffmpeg", "-version"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)

        if result.returncode == 0:
            logging.info("FFmpeg encontrado no sistema")
            return True
        else:
            logging.warning("FFmpeg não encontrado no sistema, verificando pasta local")
            return False
    except Exception as e:
        logging.warning(f"Erro ao verificar FFmpeg no sistema: {e}")
        return False


def verificar_ffmpeg_local(destino="ffmpeg"):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")

    ffmpeg_exe = os.path.join(base_path, destino, "bin", "ffmpeg.exe")

    if os.path.exists(ffmpeg_exe):
        logging.info(f"FFmpeg encontrado localmente em: {ffmpeg_exe}")
        return True
    else:
        logging.warning(f"FFmpeg não encontrado localmente em: {ffmpeg_exe}")
        return False


def baixar_ffmpeg(destino="ffmpeg"):
    try:
        logging.info("Verificando se o FFmpeg já está disponível")

        if verificar_ffmpeg():
            logging.info("FFmpeg já disponível no sistema, não será baixado")
            return True

        if verificar_ffmpeg_local(destino):
            logging.info("FFmpeg já existe localmente, configurando PATH")
            configurar_ffmpeg()
            return True

        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".")

        destino_completo = os.path.join(base_path, destino)
        os.makedirs(destino_completo, exist_ok=True)
        zip_path = os.path.join(destino_completo, "ffmpeg.zip")

        QMessageBox.information(None, "Download do FFmpeg",
                              "O FFmpeg não foi encontrado no sistema. Iniciando o download...\n"
                              "Este processo será realizado apenas uma vez.")

        try:
            logging.info("Baixando FFmpeg...")
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            urllib.request.urlretrieve(url, zip_path)
            logging.info("Download do FFmpeg concluído")

            logging.info("Extraindo arquivos FFmpeg...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(destino_completo)
            logging.info("Extração concluída")

            if os.path.exists(zip_path):
                os.remove(zip_path)
                logging.info("Arquivo zip removido")

            bin_encontrado = False
            for root, dirs, _ in os.walk(destino_completo):
                for d in dirs:
                    if "bin" in d:
                        src = os.path.join(root, d)
                        dest_bin = os.path.join(destino_completo, "bin")
                        if src != dest_bin and not os.path.exists(dest_bin):
                            logging.info(f"Movendo pasta bin de {src} para {dest_bin}")
                            os.rename(src, dest_bin)
                            bin_encontrado = True
                            break
                if bin_encontrado:
                    break

            if verificar_ffmpeg_local(destino):
                logging.info("FFmpeg instalado com sucesso")
                configurar_ffmpeg()
                return True
            else:
                raise Exception("Falha ao verificar instalação do FFmpeg")

        except Exception as download_error:
            logging.error(f"Erro durante download/extração do FFmpeg: {download_error}")
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise download_error

    except Exception as e:
        logging.error(f"Erro ao baixar/configurar FFmpeg: {e}")
        logging.exception("Detalhes do erro:")
        QMessageBox.warning(None, "Erro FFmpeg",
                          "Ocorreu um erro ao instalar o FFmpeg.\n"
                          "O aplicativo tentará continuar, mas os downloads de áudio podem falhar.\n\n"
                          f"Erro: {str(e)}")
        return False


def configurar_ffmpeg():
    try:
        logging.info("Configurando caminhos do FFmpeg")
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            logging.info(f"Executando a partir do executável congelado: {base_path}")
        else:
            base_path = os.path.abspath(".")
            logging.info(f"Executando a partir do script: {base_path}")

        ffmpeg_path = os.path.join(base_path, "ffmpeg", "bin")
        logging.info(f"Caminho do FFmpeg: {ffmpeg_path}")

        if not os.path.exists(ffmpeg_path):
            logging.warning(f"Pasta FFmpeg não encontrada em: {ffmpeg_path}")

        if ffmpeg_path not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + ffmpeg_path

        logging.debug(f"PATH atual: {os.environ['PATH']}")
    except Exception as e:
        logging.error(f"Erro ao configurar caminhos do FFmpeg: {e}")
        logging.exception("Detalhes do erro:")


class DownloadCancelled(Exception):
    """Exceção interna usada para interromper um download em andamento."""
    pass


class DownloadProgress(QObject):
    progress_update = Signal(float, str)
    status_update = Signal(str)
    download_complete = Signal(str, str)   # título, pasta de destino
    download_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.cancel_requested = False

    def progress_hook(self, d):
        try:
            if self.cancel_requested:
                # Interrompe o download de forma controlada em vez de deixar
                # o processo continuar "preso" em segundo plano.
                raise DownloadCancelled("Download cancelado pelo usuário")

            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%')
                p = re.sub(r'\x1b\[[0-9;]*m', '', p)  # remove códigos ANSI de cor
                p = p.replace('%', '').strip()
                try:
                    percent = float(p)
                except ValueError:
                    percent = 0

                speed = d.get('_speed_str', '').strip() or "—"
                eta = d.get('_eta_str', '').strip() or "—"
                info = f"Velocidade: {speed}   |   Tempo restante: {eta}"

                self.progress_update.emit(percent, info)

            elif d['status'] == 'finished':
                # NÃO significa que o processo terminou: para vídeos MP4 ainda falta
                # mesclar vídeo+áudio, e para MP3 ainda falta extrair o áudio.
                # Emitir "concluído" aqui era a causa do bug de downloads que pareciam
                # falhar/ficar incompletos, pois a UI liberava o botão antes da hora.
                self.status_update.emit("Processando arquivo (mesclando/convertendo)...")

            elif d['status'] == 'error':
                self.download_error.emit(str(d.get('error', 'Erro desconhecido')))
        except DownloadCancelled:
            raise
        except Exception as e:
            logging.error(f"Erro no hook de progresso: {e}")
            self.download_error.emit(f"Erro no progresso: {e}")


STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1f26;
    color: #e8e8ec;
    font-family: 'Segoe UI', sans-serif;
}
QLabel {
    color: #c7c7d1;
    font-size: 13px;
}
QLabel#title {
    color: #ffffff;
    font-size: 18px;
    font-weight: 600;
}
QLabel#status {
    color: #9a9aa5;
    font-size: 12px;
}
QLineEdit, QComboBox {
    background-color: #2a2b34;
    border: 1px solid #3a3b46;
    border-radius: 6px;
    padding: 7px 9px;
    color: #f0f0f3;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #FF3B30;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QPushButton {
    background-color: #2f303b;
    border: 1px solid #3a3b46;
    border-radius: 6px;
    padding: 8px 14px;
    color: #e8e8ec;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #383946;
}
QPushButton:disabled {
    color: #6b6c76;
}
QPushButton#downloadBtn {
    background-color: #FF3B30;
    border: none;
    color: white;
    font-weight: 600;
    padding: 10px 16px;
    font-size: 14px;
}
QPushButton#downloadBtn:hover {
    background-color: #e6352b;
}
QPushButton#downloadBtn:disabled {
    background-color: #7a3733;
    color: #d9d9d9;
}
QPushButton#cancelBtn {
    background-color: transparent;
    border: 1px solid #FF3B30;
    color: #FF3B30;
}
QPushButton#cancelBtn:hover {
    background-color: rgba(255, 59, 48, 0.12);
}
QProgressBar {
    border: 1px solid #3a3b46;
    border-radius: 6px;
    text-align: center;
    height: 22px;
    background-color: #2a2b34;
    color: #f0f0f3;
}
QProgressBar::chunk {
    background-color: #FF3B30;
    border-radius: 5px;
}
QFrame#divider {
    background-color: #3a3b46;
    max-height: 1px;
}
"""


class YouLoader(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            logging.info("Iniciando a interface do YouTube Downloader")
            self.setWindowTitle("YouLoader")
            self.setMinimumSize(480, 460)
            self.resize(480, 460)

            self.default_download_folder = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
            logging.info(f"Pasta de downloads padrão: {self.default_download_folder}")

            self.setup_icon()
            self.setup_logo()

            self.progress_manager = DownloadProgress()
            self.progress_manager.progress_update.connect(self.update_progress)
            self.progress_manager.status_update.connect(self.update_status_text)
            self.progress_manager.download_complete.connect(self.download_finished)
            self.progress_manager.download_error.connect(self.download_error)

            self.last_dest_folder = self.default_download_folder
            self.is_downloading = False

            self.setStyleSheet(STYLESHEET)
            self.init_ui()
            logging.info("Interface inicializada com sucesso")
        except Exception as e:
            logging.critical(f"Erro ao inicializar a interface: {e}")
            logging.exception("Detalhes do erro:")
            QMessageBox.critical(None, "Erro de Inicialização",
                                 f"Erro ao inicializar a interface: {e}\n"
                                 f"Consulte o log para mais detalhes: {log_file}")
            raise

    def setup_icon(self):
        try:
            icon_path = resource_path("app-icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logging.info(f"Ícone carregado de: {icon_path}")
            else:
                logging.warning(f"Ícone não encontrado em: {icon_path}")
        except Exception as e:
            logging.error(f"Erro ao configurar ícone: {e}")

    def setup_logo(self):
        try:
            logo_path = resource_path("app-logo.png")
            if os.path.exists(logo_path):
                self.logo_pixmap = QPixmap(logo_path)
                logging.info(f"Logo carregado de: {logo_path}")
            else:
                logging.warning(f"Logo não encontrado em: {logo_path}")
                self.logo_pixmap = QPixmap(64, 60)
                self.logo_pixmap.fill(Qt.red)
        except Exception as e:
            logging.error(f"Erro ao configurar logo: {e}")
            self.logo_pixmap = QPixmap(64, 60)
            self.logo_pixmap.fill(Qt.red)

    def init_ui(self):
        try:
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(24, 20, 24, 20)
            main_layout.setSpacing(12)

            # Cabeçalho com logo + título
            header_layout = QHBoxLayout()
            logo_label = QLabel()
            logo_label.setPixmap(self.logo_pixmap)
            logo_label.setFixedSize(40, 38)
            logo_label.setScaledContents(True)

            title_label = QLabel("YouLoader")
            title_label.setObjectName("title")

            header_layout.addWidget(logo_label)
            header_layout.addSpacing(8)
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            main_layout.addLayout(header_layout)

            divider = QFrame()
            divider.setObjectName("divider")
            divider.setFrameShape(QFrame.HLine)
            main_layout.addWidget(divider)
            main_layout.addSpacing(4)

            # Campo de URL com botão de colar
            url_label = QLabel("Link do vídeo do YouTube")
            main_layout.addWidget(url_label)

            url_row = QHBoxLayout()
            self.url_input = QLineEdit()
            self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
            self.url_input.textChanged.connect(self.clear_url_warning)
            self.paste_btn = QPushButton("Colar")
            self.paste_btn.setFixedWidth(70)
            self.paste_btn.clicked.connect(self.paste_from_clipboard)
            url_row.addWidget(self.url_input)
            url_row.addWidget(self.paste_btn)
            main_layout.addLayout(url_row)

            # Qualidade e formato lado a lado
            options_row = QHBoxLayout()

            quality_col = QVBoxLayout()
            quality_label = QLabel("Qualidade")
            self.quality_combo = QComboBox()
            self.quality_combo.addItems(["Alta", "Média", "Baixa"])
            quality_col.addWidget(quality_label)
            quality_col.addWidget(self.quality_combo)

            format_col = QVBoxLayout()
            format_label = QLabel("Formato")
            self.format_combo = QComboBox()
            self.format_combo.addItems(["mp4", "mp3"])
            self.format_combo.currentTextChanged.connect(self.on_format_changed)
            format_col.addWidget(format_label)
            format_col.addWidget(self.format_combo)

            options_row.addLayout(quality_col)
            options_row.addLayout(format_col)
            main_layout.addLayout(options_row)

            # Pasta de destino
            folder_label = QLabel("Pasta de destino")
            main_layout.addWidget(folder_label)

            folder_layout = QHBoxLayout()
            self.folder_input = QLineEdit()
            self.folder_input.setText(self.default_download_folder)
            self.folder_btn = QPushButton("Selecionar")
            self.folder_btn.clicked.connect(self.choose_folder)
            folder_layout.addWidget(self.folder_input)
            folder_layout.addWidget(self.folder_btn)
            main_layout.addLayout(folder_layout)

            main_layout.addSpacing(6)

            # Botões de ação
            action_row = QHBoxLayout()
            self.download_btn = QPushButton("Baixar")
            self.download_btn.setObjectName("downloadBtn")
            self.download_btn.clicked.connect(self.download)

            self.cancel_btn = QPushButton("Cancelar")
            self.cancel_btn.setObjectName("cancelBtn")
            self.cancel_btn.clicked.connect(self.cancel_download)
            self.cancel_btn.setVisible(False)

            action_row.addWidget(self.download_btn)
            action_row.addWidget(self.cancel_btn)
            main_layout.addLayout(action_row)

            # Progresso
            progress_layout = QVBoxLayout()
            progress_layout.setSpacing(6)

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setFormat("%p%")

            self.status_label = QLabel("Pronto para baixar")
            self.status_label.setObjectName("status")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setWordWrap(True)

            progress_layout.addWidget(self.progress_bar)
            progress_layout.addWidget(self.status_label)

            main_layout.addLayout(progress_layout)

            # Botão "Abrir pasta", só aparece após concluir
            self.open_folder_btn = QPushButton("Abrir pasta de destino")
            self.open_folder_btn.clicked.connect(self.open_destination_folder)
            self.open_folder_btn.setVisible(False)
            main_layout.addWidget(self.open_folder_btn)

            main_layout.addStretch()

            logging.info("UI configurada com sucesso")
        except Exception as e:
            logging.error(f"Erro ao inicializar UI: {e}")
            logging.exception("Detalhes do erro:")
            raise

    def on_format_changed(self, fmt):
        # A qualidade só faz sentido para vídeo; em áudio, sempre extraímos o melhor.
        self.quality_combo.setEnabled(fmt == "mp4")

    def clear_url_warning(self):
        self.url_input.setStyleSheet("")

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.setText(text)

    def choose_folder(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Destino", self.default_download_folder)
            if folder:
                self.folder_input.setText(folder)
                logging.info(f"Pasta de destino selecionada: {folder}")
        except Exception as e:
            logging.error(f"Erro ao selecionar pasta: {e}")
            QMessageBox.warning(self, "Erro", f"Erro ao selecionar pasta: {e}")

    def open_destination_folder(self):
        if self.last_dest_folder and os.path.isdir(self.last_dest_folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_dest_folder))

    def cancel_download(self):
        if self.is_downloading:
            self.progress_manager.cancel_requested = True
            self.status_label.setText("Cancelando...")

    def download(self):
        try:
            url = self.url_input.text().strip()
            quality = self.quality_combo.currentText()
            format_type = self.format_combo.currentText()
            folder = self.folder_input.text().strip()

            logging.info(f"Iniciando download: URL={url}, Qualidade={quality}, Formato={format_type}, Pasta={folder}")

            if not url:
                QMessageBox.warning(self, "Aviso", "Insira o link do vídeo.")
                return

            if not YOUTUBE_URL_RE.match(url):
                self.url_input.setStyleSheet("border: 1px solid #FF3B30;")
                QMessageBox.warning(self, "Link inválido",
                                     "Esse não parece ser um link válido do YouTube.\n"
                                     "Use um link no formato:\n"
                                     "https://www.youtube.com/watch?v=XXXXXXXX\n"
                                     "https://youtu.be/XXXXXXXX")
                return

            if not folder:
                folder = self.default_download_folder
                logging.info(f"Pasta não especificada, usando padrão: {folder}")

            if not os.path.isdir(folder):
                try:
                    os.makedirs(folder, exist_ok=True)
                except Exception:
                    QMessageBox.warning(self, "Aviso", "A pasta de destino informada é inválida.")
                    return

            self.last_dest_folder = folder
            self.progress_manager.cancel_requested = False

            common_opts = {
                'outtmpl': os.path.join(folder, '%(title).150s.%(ext)s'),
                'noplaylist': True,
                'windowsfilenames': True,
                'restrictfilenames': False,
                'retries': 10,
                'fragment_retries': 10,
                'socket_timeout': 30,
                'concurrent_fragment_downloads': 4,
                'progress_hooks': [self.progress_manager.progress_hook],
                'quiet': True,
                'no_warnings': False,
            }

            if format_type == "mp4":
                if quality == "Alta":
                    format_yt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif quality == "Média":
                    format_yt = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]"
                else:
                    format_yt = "worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst"

                ydl_opts = {
                    **common_opts,
                    'format': format_yt,
                    'merge_output_format': 'mp4',
                    # Antes o app forçava reencode (-c:v libx264 -c:a aac) em TODO
                    # download, o que era lento e podia falhar/travar em vídeos longos
                    # ou em máquinas mais fracas. Como os formatos já são filtrados
                    # para mp4/m4a (H.264/AAC), basta remuxar sem recodificar.
                    'postprocessor_args': {
                        'merger': ['-c', 'copy'],
                    },
                }

            else:  # mp3
                format_yt = "bestaudio/best"

                ydl_opts = {
                    **common_opts,
                    'format': format_yt,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }

            logging.info(f"Formato yt-dlp: {format_yt}")
            logging.info(f"Opções yt-dlp: {ydl_opts}")

            self.progress_bar.setValue(0)
            self.status_label.setText("Iniciando download...")
            self.open_folder_btn.setVisible(False)
            self.download_btn.setEnabled(False)
            self.download_btn.setText("Baixando...")
            self.cancel_btn.setVisible(True)
            self.is_downloading = True

            def download_thread():
                try:
                    logging.info(f"Thread de download iniciada para URL: {url}")
                    # Uma única chamada faz a extração de metadados E o download,
                    # em vez das duas chamadas separadas (extract_info + download)
                    # que existiam antes. Duas requisições distintas ao YouTube
                    # aumentavam a chance de a segunda ser bloqueada/expirar,
                    # o que também contribuía para o "às vezes não baixa".
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        title = info.get('title', 'vídeo') if info else 'vídeo'
                    logging.info("Download concluído com sucesso")
                    # Só sinaliza "concluído" depois que download() retorna de fato,
                    # ou seja, depois que toda a mesclagem/conversão terminou.
                    self.progress_manager.download_complete.emit(title, folder)
                except DownloadCancelled:
                    logging.info("Download cancelado pelo usuário")
                    self.progress_manager.download_error.emit("__CANCELLED__")
                except Exception as e:
                    logging.error(f"Erro no download: {e}")
                    logging.exception("Detalhes do erro:")
                    self.progress_manager.download_error.emit(str(e))

            Thread(target=download_thread, daemon=True).start()

        except Exception as e:
            logging.error(f"Erro ao iniciar download: {e}")
            logging.exception("Detalhes do erro:")
            self.status_label.setText("Erro ao iniciar download")
            self.reset_download_controls()
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar download: {e}")

    def reset_download_controls(self):
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Baixar")
        self.cancel_btn.setVisible(False)
        self.is_downloading = False

    def update_progress(self, percent, info):
        try:
            self.progress_bar.setValue(int(percent))
            self.status_label.setText(info)
            logging.debug(f"Progresso: {percent}% - {info}")
        except Exception as e:
            logging.error(f"Erro ao atualizar progresso: {e}")

    def update_status_text(self, text):
        self.status_label.setText(text)

    def download_finished(self, title, dest_folder):
        try:
            self.progress_bar.setValue(100)
            self.status_label.setText("Download concluído com sucesso!")
            self.reset_download_controls()
            self.open_folder_btn.setVisible(True)

            logging.info(f"Download concluído em: {dest_folder}")

            QMessageBox.information(self, "Sucesso", f'"{title}" baixado com sucesso em:\n{dest_folder}')
        except Exception as e:
            logging.error(f"Erro ao finalizar download: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao finalizar download: {e}")

    def download_error(self, error_msg):
        try:
            self.progress_bar.setValue(0)
            self.reset_download_controls()

            if error_msg == "__CANCELLED__":
                self.status_label.setText("Download cancelado")
                return

            self.status_label.setText("Erro no download")
            logging.error(f"Erro reportado no download: {error_msg}")
            QMessageBox.critical(self, "Erro", f"Erro ao baixar vídeo:\n{error_msg}")
        except Exception as e:
            logging.error(f"Erro ao processar falha de download: {e}")


def main():
    try:
        logging.info("=== INICIANDO APLICATIVO ===")
        logging.info(f"Diretório atual: {os.getcwd()}")
        logging.info(f"Diretório do script: {os.path.dirname(os.path.abspath(__file__))}")
        logging.info(f"Arquivos presentes: {os.listdir()}")

        app = QApplication(sys.argv)
        logging.info("QApplication criada com sucesso")

        try:
            configurar_ffmpeg()
            baixar_ffmpeg()
        except Exception as e:
            logging.error(f"Erro na configuração do FFmpeg: {e}")
            logging.exception("Detalhes do erro:")

        window = YouLoader()
        logging.info("Janela principal criada")

        window.show()
        logging.info("Janela exibida, iniciando loop de eventos")

        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"ERRO FATAL NA FUNÇÃO MAIN: {e}")
        logging.exception("Detalhes do erro:")
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Erro Fatal",
                                 f"Um erro fatal ocorreu ao iniciar o aplicativo.\n"
                                 f"Detalhes do erro foram salvos em:\n{log_file}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
