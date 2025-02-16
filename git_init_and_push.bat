@echo off
chcp 65001
echo ===== 初始化Git倉庫並上傳到GitHub =====

:: 初始化git倉庫（如果尚未初始化）
if not exist .git (
    git init
    git remote add origin https://github.com/aken1023/Shift-Handover-System.git
)

:: 添加所有文件
git add .

:: 提示用戶輸入commit信息
set /p commit_msg="請輸入commit信息: "

:: 提交更改
git commit -m "%commit_msg%"

:: 推送到遠程倉庫
git push -u origin main

echo ===== 上傳完成 =====
pause 