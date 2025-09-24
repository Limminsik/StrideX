@echo off
echo Building StrideX Desktop Application...

REM 가상환경 활성화 (있는 경우)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM 의존성 설치
pip install -r requirements.txt
pip install pyinstaller

REM PyInstaller로 빌드
pyinstaller desktop\main.py ^
  --name "StrideX Dashboard" ^
  --onefile --noconsole ^
  --icon assets\stridex.ico ^
  --add-data "backend\static;backend\static" ^
  --add-data "backend\data;backend\data" ^
  --add-data "assets\stridex.ico;assets" ^
  --hidden-import uvicorn ^
  --hidden-import fastapi ^
  --hidden-import pywebview

echo Build completed! Check dist\ folder for StrideX Dashboard.exe
pause
