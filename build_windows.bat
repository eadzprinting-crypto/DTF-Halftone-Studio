@echo off
setlocal
cd /d "%~dp0"
echo Building DTF Halftone Studio for Windows...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --windowed --onefile --name DTF_Halftone_Studio dtf_halftone_studio.py
if exist "dist\DTF_Halftone_Studio.exe" (
  echo.
  echo SUCCESS: dist\DTF_Halftone_Studio.exe
) else (
  echo BUILD FAILED. Check the messages above.
)
pause
