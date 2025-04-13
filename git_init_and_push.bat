@echo off
chcp 65001 >nul
echo ===== 初始化Git倉庫並上傳到GitHub =====

:: 檢查git是否已安裝
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 錯誤：未找到git，請先安裝git
    pause
    exit /b 1
)

:: 初始化git倉庫（如果尚未初始化）
if not exist .git (
    echo 正在初始化git倉庫...
    git init
    if %ERRORLEVEL% neq 0 (
        echo 錯誤：初始化git倉庫失敗
        pause
        exit /b 1
    )
    
    echo 正在添加遠程倉庫...
    git remote add origin https://github.com/aken1023/MP_Shift-Transfer-System.git
    if %ERRORLEVEL% neq 0 (
        echo 錯誤：添加遠程倉庫失敗
        pause
        exit /b 1
    )
)

:: 檢查當前分支
git branch --show-current >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 正在創建main分支...
    git checkout -b main
)

:: 顯示當前狀態
echo 正在檢查文件狀態...
git status

:: 添加所有文件
echo 正在添加所有文件...
git add --all
if %ERRORLEVEL% neq 0 (
    echo 錯誤：添加文件失敗
    pause
    exit /b 1
)

:: 檢查是否有更改需要提交
git status --porcelain | findstr /r "^[MADRCU]" >nul
if %ERRORLEVEL% neq 0 (
    echo 沒有需要提交的更改
    pause
    exit /b 0
)

:: 顯示即將提交的文件
echo 即將提交以下文件：
git status --porcelain

:: 提示用戶輸入commit信息
set /p commit_msg="請輸入commit信息: "

:: 提交更改
echo 正在提交更改...
git commit -m "%commit_msg%"
if %ERRORLEVEL% neq 0 (
    echo 錯誤：提交更改失敗
    pause
    exit /b 1
)

:: 推送到遠程倉庫
echo 正在推送到GitHub...
git push -u origin main
if %ERRORLEVEL% neq 0 (
    echo 錯誤：推送失敗
    pause
    exit /b 1
)

echo ===== 上傳完成 =====
pause 