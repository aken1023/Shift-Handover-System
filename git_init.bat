@echo off
chcp 65001
echo ===== 初始化新的 Git 倉庫 =====

:: 創建 README.md
echo "# Shift-Handover-System" >> README.md

:: 初始化 git 倉庫
echo 初始化 Git 倉庫...
git init

:: 添加 README.md
echo 添加 README.md...
git add README.md

:: 提交
echo 創建首次提交...
git commit -m "first commit"

:: 創建並切換到 main 分支
echo 設置 main 分支...
git branch -M main

:: 添加遠程倉庫
echo 添加遠程倉庫...
git remote add origin https://github.com/aken1023/Shift-Handover-System.git

:: 推送到遠程倉庫
echo 推送到 GitHub...
git push -u origin main

echo ===== 初始化完成 =====
pause 