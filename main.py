import sys
import os
import traceback
import urllib.request
import zipfile
import logging
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
                                   QPushButton, QFileDialog, QMessageBox, QProgressBar)
    from PySide6.QtCore import Qt, QStandardPaths, Signal, QObject
    from PySide6.QtGui import QIcon, QPixmap
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
    except:
        pass
    sys.exit(1)


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
        import subprocess
        import shutil

        # Primeiro tenta encontrar o FFmpeg no PATH do sistema
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            logging.info(f"FFmpeg encontrado no sistema em: {ffmpeg_path}")
            return True

        # Se não encontrou no PATH, tenta executar diretamente
        result = subprocess.run(["ffmpeg", "-version"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True,
                              shell=True)
        
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

        # Primeiro verifica se o FFmpeg já está instalado no sistema
        if verificar_ffmpeg():
            logging.info("FFmpeg já disponível no sistema, não será baixado")
            return True

        # Depois verifica se já existe localmente
        if verificar_ffmpeg_local(destino):
            logging.info("FFmpeg já existe localmente, configurando PATH")
            configurar_ffmpeg()
            return True

        # Se não encontrou, prepara para download
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".")

        destino_completo = os.path.join(base_path, destino)
        os.makedirs(destino_completo, exist_ok=True)
        zip_path = os.path.join(destino_completo, "ffmpeg.zip")

        # Informa ao usuário sobre o download
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

            # Remove o arquivo zip após extração
            if os.path.exists(zip_path):
                os.remove(zip_path)
                logging.info("Arquivo zip removido")

            # Procura e move a pasta bin para o local correto
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

            # Verifica se a instalação foi bem-sucedida
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

        os.environ["PATH"] += os.pathsep + ffmpeg_path

        logging.debug(f"PATH atual: {os.environ['PATH']}")
    except Exception as e:
        logging.error(f"Erro ao configurar caminhos do FFmpeg: {e}")
        logging.exception("Detalhes do erro:")


class DownloadProgress(QObject):
    progress_update = Signal(float, str)
    download_complete = Signal()
    download_error = Signal(str)

    def __init__(self):
        super().__init__()

    def progress_hook(self, d):
        try:
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
        except Exception as e:
            logging.error(f"Erro no hook de progresso: {e}")
            self.download_error.emit(f"Erro no progresso: {e}")


class YouLoader(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            logging.info("Iniciando a interface do YouTube Downloader")
            self.setWindowTitle("YouLoader")
            self.setFixedSize(500, 400)

            self.default_download_folder = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
            logging.info(f"Pasta de downloads padrão: {self.default_download_folder}")

            self.setup_icon()
            self.setup_logo()

            self.progress_manager = DownloadProgress()
            self.progress_manager.progress_update.connect(self.update_progress)
            self.progress_manager.download_complete.connect(self.download_finished)
            self.progress_manager.download_error.connect(self.download_error)

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
            main_layout.setSpacing(10)

            logo_layout = QHBoxLayout()

            logo_label = QLabel()
            logo_label.setPixmap(self.logo_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)

            logo_layout.addStretch()
            logo_layout.addWidget(logo_label)
            logo_layout.addStretch()
            logo_label.setFixedSize(64, 60)
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

            logging.info("UI configurada com sucesso")
        except Exception as e:
            logging.error(f"Erro ao inicializar UI: {e}")
            logging.exception("Detalhes do erro:")
            raise

    def choose_folder(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Destino", self.default_download_folder)
            if folder:
                self.folder_input.setText(folder)
                logging.info(f"Pasta de destino selecionada: {folder}")
        except Exception as e:
            logging.error(f"Erro ao selecionar pasta: {e}")
            QMessageBox.warning(self, "Erro", f"Erro ao selecionar pasta: {e}")

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

            if not folder:
                folder = self.default_download_folder
                logging.info(f"Pasta não especificada, usando padrão: {folder}")

            if format_type == "mp4":
                if quality == "Alta":
                    format_yt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/mp4"
                elif quality == "Média":
                    format_yt = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/mp4"
                else:
                    format_yt = "worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/mp4"

                ext = "mp4"

                ydl_opts = {
                    'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
                    'format': format_yt,
                    'progress_hooks': [self.progress_manager.progress_hook],
                    'merge_output_format': 'mp4',
                    'postprocessor_args': [
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                    ],
                    'verbose': True,
                }

            else:  # mp3
                format_yt = "bestaudio/best"
                ext = "mp3"

                ydl_opts = {
                    'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
                    'format': format_yt,
                    'progress_hooks': [self.progress_manager.progress_hook],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'verbose': True,
                }

            logging.info(f"Formato yt-dlp: {format_yt}")
            logging.info(f"Opções yt-dlp: {ydl_opts}")

            self.progress_bar.setValue(0)
            self.status_label.setText("Iniciando download...")
            self.download_btn.setEnabled(False)
            self.download_btn.setText("Baixando...")

            def download_thread():
                try:
                    logging.info(f"Thread de download iniciada para URL: {url}")
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        logging.info(
                            f"Informações do vídeo: Título={info.get('title')}, Formatos disponíveis={info.get('formats')}")
                        ydl.download([url])
                    logging.info("Download concluído com sucesso")
                except Exception as e:
                    logging.error(f"Erro no download: {e}")
                    logging.exception("Detalhes do erro:")
                    self.progress_manager.download_error.emit(str(e))

            Thread(target=download_thread, daemon=True).start()

        except Exception as e:
            logging.error(f"Erro ao iniciar download: {e}")
            logging.exception("Detalhes do erro:")
            self.status_label.setText("Erro ao iniciar download")
            self.download_btn.setEnabled(True)
            self.download_btn.setText("Baixar")
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar download: {e}")

    def update_progress(self, percent, info):
        try:
            self.progress_bar.setValue(int(percent))
            self.status_label.setText(info)
            logging.debug(f"Progresso: {percent}% - {info}")
        except Exception as e:
            logging.error(f"Erro ao atualizar progresso: {e}")

    def download_finished(self):
        try:
            self.progress_bar.setValue(100)
            self.status_label.setText("Download concluído com sucesso!")
            self.download_btn.setEnabled(True)
            self.download_btn.setText("Baixar")

            dest_folder = self.folder_input.text() or self.default_download_folder
            logging.info(f"Download concluído em: {dest_folder}")

            QMessageBox.information(self, "Sucesso", f"Download concluído em:\n{dest_folder}")
        except Exception as e:
            logging.error(f"Erro ao finalizar download: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao finalizar download: {e}")

    def download_error(self, error_msg):
        try:
            self.progress_bar.setValue(0)
            self.status_label.setText("Erro no download")
            self.download_btn.setEnabled(True)
            self.download_btn.setText("Baixar")

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

        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"ERRO FATAL NA FUNÇÃO MAIN: {e}")
        logging.exception("Detalhes do erro:")
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Erro Fatal",
                                 f"Um erro fatal ocorreu ao iniciar o aplicativo.\n"
                                 f"Detalhes do erro foram salvos em:\n{log_file}")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()