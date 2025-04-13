@echo off
chcp 65001
echo ===== Start uploading to GitHub =====

:: Check for .env file
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create .env file with your API keys
    pause
    exit /b 1
)

:: Check for .gitignore
if not exist .gitignore (
    echo ERROR: .gitignore file not found!
    echo Please create .gitignore file first
    pause
    exit /b 1
)

:: Check git configuration
git config --list | findstr "user.name" > nul
if errorlevel 1 (
    echo Setting up git user name...
    set /p git_name="Enter your GitHub username: "
    git config --global user.name "%git_name%"
)

git config --list | findstr "user.email" > nul
if errorlevel 1 (
    echo Setting up git email...
    set /p git_email="Enter your GitHub email: "
    git config --global user.email "%git_email%"
)

:: Remove existing remote if any
git remote remove origin

:: Add correct remote
echo Setting up correct repository...
git remote add origin https://github.com/aken1023/MP_Shift-Transfer-System.git

:: Check if git is initialized
if not exist .git (
    echo Initializing git repository...
    git init
)

:: Check current branch
for /f "tokens=* USEBACKQ" %%F in (`git branch --show-current`) do set current_branch=%%F
echo Current branch: %current_branch%

:: If this is a new repository, create and switch to main branch
if "%current_branch%"=="" (
    echo Creating main branch...
    git checkout -b main
)

:: Clean any cached files that should be ignored
git rm -r --cached .
git add .

:: Get commit message
set /p commit_msg="Enter commit message: "

:: Commit changes
git commit -m "%commit_msg%"

:: Push to remote with credential helper
echo Pushing to remote repository...
git config --global credential.helper store
git push -u origin main

if errorlevel 1 (
    echo Push failed! Please check:
    echo 1. No sensitive data in commits
    echo 2. .gitignore is properly configured
    echo 3. .env file is not being tracked
    echo.
    echo Press any key to try pushing again...
    pause > nul
    git push -u origin main
)

echo ===== Upload completed =====
pause 