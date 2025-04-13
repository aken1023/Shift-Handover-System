@echo off
echo ===== Git Push Script =====

:: Initialize git if not already initialized
if not exist .git (
    echo Initializing git repository...
    git init
    git remote add origin https://github.com/aken1023/MP_Shift-Transfer-System.git
)

:: Force add all files
echo Adding all files...
git add -f .

:: Show status
echo Current status:
git status

:: Get commit message
set /p commit_msg="Enter commit message: "

:: Commit changes
echo Committing changes...
git commit -m "%commit_msg%"

:: Force push to main branch
echo Pushing to GitHub...
git push -f origin main

echo ===== Push Completed =====
pause
