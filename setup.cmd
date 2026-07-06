@echo off
echo ====================================
echo   CREANT ENTORN PROJECTE PYTHON
echo ====================================

REM Crear entorn virtual
py -3.14 -m venv .venv

REM Actualitzar pip usant el Python del venv (sense activar-lo)
.venv\Scripts\python -m pip install --upgrade pip

echo.
echo Instal·lant dependències...
.venv\Scripts\python -m pip install -r requirements.txt

echo.
echo ====================================
echo   ✔ ENTORN CREAT CORRECTAMENT
echo ====================================
pause