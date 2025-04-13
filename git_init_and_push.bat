@echo off
echo ===== Git Push Script =====

:: Initialize git if not already initialized
if not exist .git (
    echo Initializing git repository...
    git init
    git remote add origin https://github.com/aken1023/MP_Shift-Transfer-System.git
)

:: Remove sensitive files from git tracking and history
echo Removing sensitive files from tracking and history...
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all
git filter-branch --force --index-filter "git rm -r --cached --ignore-unmatch uploads/" --prune-empty --tag-name-filter cat -- --all
git filter-branch --force --index-filter "git rm -r --cached --ignore-unmatch records/" --prune-empty --tag-name-filter cat -- --all
git filter-branch --force --index-filter "git rm -r --cached --ignore-unmatch ssl/" --prune-empty --tag-name-filter cat -- --all

:: Clean up and optimize repository
echo Cleaning up repository...
git for-each-ref --format='delete %(refname)' refs/original/ | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

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

:: Force push to main branch
echo Pushing to GitHub...
git push -f origin main

echo ===== Push Completed =====
pause
