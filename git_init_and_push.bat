@echo off
echo ===== Git Push Script =====

:: Initialize git if not already initialized
if not exist .git (
    echo Initializing git repository...
    git init
    git remote add origin https://github.com/aken1023/MP_Shift-Transfer-System.git
)

:: Remove sensitive files from git tracking
echo Removing sensitive files from tracking...
git rm --cached .env
git rm --cached -r uploads/
git rm --cached -r records/
git rm --cached -r ssl/

:: Add all files except those in .gitignore
echo Adding files...
git add .

:: Show status
echo Current status:
git status

:: Get commit message
set /p commit_msg="Enter commit message: "

:: Commit changes
echo Committing changes...
git commit -m "%commit_msg%"

:: Push to main branch
echo Pushing to GitHub...
git push origin main

echo ===== Push Completed =====
pause
