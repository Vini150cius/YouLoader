@echo off
echo ===================================
echo  YouLoader - Script de Compilacao
echo ===================================
echo.

REM Verifica se o ambiente virtual existe, se não, cria
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
    echo Ambiente virtual criado!
) else (
    echo Ambiente virtual encontrado.
)

REM Ativa o ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate

REM Instala ou atualiza as dependências
echo Instalando/atualizando dependencias...
pip install -U pip
pip install -U pyinstaller
pip install -U PySide6
pip install -U yt-dlp

REM Limpa diretórios de builds anteriores
echo Limpando builds anteriores...
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist *.spec del *.spec

REM Executa o PyInstaller
echo.
echo Iniciando compilacao com PyInstaller...
echo.

pyinstaller ^
    --name=YouLoader ^
    --onefile ^
    --windowed ^
    --icon=app-icon.ico ^
    --add-data="app-icon.png;." ^
    --add-data="app-logo.png;." ^
    --hidden-import=yt_dlp ^
    --hidden-import=PySide6 ^
    --hidden-import=urllib.request ^
    --hidden-import=zipfile ^
    --hidden-import=logging ^
    --clean ^
    main.py

REM Verifica se a compilação foi bem-sucedida
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================
    echo  Compilacao concluida com sucesso!
    echo  O executavel esta em: dist\YouLoader.exe
    echo ===================================
    
    REM Cria arquivo README na pasta dist
    echo # YouLoader > dist\README.txt
    echo. >> dist\README.txt
    echo Aplicativo para download de videos do YouTube >> dist\README.txt
    echo. >> dist\README.txt
    echo Como usar: >> dist\README.txt
    echo 1. Execute YouLoader.exe >> dist\README.txt
    echo 2. Cole o link do video do YouTube >> dist\README.txt
    echo 3. Selecione as opcoes e clique em Baixar >> dist\README.txt
    echo. >> dist\README.txt
    echo O FFmpeg sera baixado automaticamente na primeira execucao, se necessario. >> dist\README.txt
) else (
    echo.
    echo ===================================
    echo  Erro na compilacao!
    echo  Verifique os erros acima.
    echo ===================================
)

REM Desativa o ambiente virtual
call venv\Scripts\deactivate

echo.
echo Pressione qualquer tecla para sair...
pause > nul