@echo off
echo ========================================
echo StrideX Desktop Dashboard Build Script
echo ========================================
echo.

echo [1/4] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del "*.spec"
echo ✓ Cleaned

echo.
echo [2/4] Installing dependencies...
pip install -r requirements.txt
echo ✓ Dependencies installed

echo.
echo [3/4] Building executable...
pyinstaller main.py --name "StrideX_Desktop" --onefile --noconsole --icon assets\stridex.ico --add-data "web;web" --add-data "assets\stridex.ico;assets" --clean
echo ✓ Build completed

echo.
echo [4/4] Finalizing...
if exist "dist\StrideX_Desktop.exe" (
    echo ✓ Executable created: dist\StrideX_Desktop.exe
    echo ✓ Size: 
    dir "dist\StrideX_Desktop.exe" | findstr "StrideX_Desktop.exe"
) else (
    echo ✗ Build failed!
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo To run: dist\StrideX_Desktop.exe
echo To test: python main.py
echo.
pause