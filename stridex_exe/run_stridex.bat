@echo off
echo Starting StrideX Dashboard...

REM 현재 디렉토리로 이동
cd /d "%~dp0"

REM Python이 설치되어 있는지 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

REM 가상환경 활성화 (있는 경우)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM 의존성 설치
pip install fastapi uvicorn pywebview requests python-multipart >nul 2>&1

REM 서버 시작
echo Starting FastAPI server...
start /B uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload

REM 서버 시작 대기
echo Waiting for server to start...
timeout /t 5 /nobreak >nul

REM 서버 상태 확인
curl -s http://127.0.0.1:8000/ >nul 2>&1
if errorlevel 1 (
    echo Server failed to start. Please check the error messages above.
    pause
    exit /b 1
)

REM 브라우저에서 열기 (한 번만)
echo Opening browser...
start http://127.0.0.1:8000

echo StrideX Dashboard is running!
echo Press any key to stop the server...
pause >nul

REM 서버 종료
taskkill /f /im python.exe >nul 2>&1
