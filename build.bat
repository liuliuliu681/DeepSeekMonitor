@echo off
chcp 65001 >nul
echo ========================================
echo   DeepSeek 余额监控器 - 打包脚本
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

echo [1/3] 安装依赖...
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
)

echo [2/3] 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del /q "*.spec"

echo [3/3] 打包为 exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "DeepSeekMonitor" ^
    --add-data "config.json;." ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成!
echo   exe 位于: dist\DeepSeekMonitor.exe
echo ========================================
pause
