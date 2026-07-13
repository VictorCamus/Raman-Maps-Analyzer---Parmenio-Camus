@echo off
echo ====================================
echo   CREANT ENTORN PROJECTE PYTHON
echo ====================================

REM Carpeta on es guardaran tots els entorns virtuals
set VENV_HOME=%USERPROFILE%\.virtualenvs

REM Nom del projecte = nom de la carpeta actual
for %%I in ("%CD%") do set PROJECT_NAME=%%~nxI

REM Ruta completa
set VENV_PATH=%VENV_HOME%\%PROJECT_NAME%

REM Crear la carpeta si no existeix
if not exist "%VENV_HOME%" mkdir "%VENV_HOME%"

REM Crear l'entorn virtual
py -3.14 -m venv "%VENV_PATH%"

REM Actualitzar pip
"%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip

echo.
echo Instal·lant dependències...
"%VENV_PATH%\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo ====================================
echo   ✔ ENTORN CREAT CORRECTAMENT
echo ====================================
echo Entorn creat a:
echo %VENV_PATH%
pause