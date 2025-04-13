@echo off
chcp 65001 >nul
echo ===== Git Repository Initialization and Push =====

:: Check if git is installed
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Git not found. Please install Git first.
    pause
    exit /b 1
)

:: Initialize git repository if not exists
if not exist .git (
    echo Initializing git repository...
    git init
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to initialize git repository
        pause
        exit /b 1
    )
    
    echo Adding remote repository...
    git remote add origin https://github.com/aken1023/MP_Shift-Transfer-System.git
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to add remote repository
        pause
        exit /b 1
    )
)

:: Check current branch
git branch --show-current >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Creating main branch...
    git checkout -b main
)

:: Show current status
echo Checking file status...
git status

:: Add all files
echo Adding all files...
git add --all
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to add files
    pause
    exit /b 1
)

:: Check if there are changes to commit
git status --porcelain | findstr /r "^[MADRCU]" >nul
if %ERRORLEVEL% neq 0 (
    echo No changes to commit
    pause
    exit /b 0
)

:: Show files to be committed
echo Files to be committed:
git status --porcelain

:: Prompt for commit message
set /p commit_msg="Enter commit message: "

:: Commit changes
echo Committing changes...
git commit -m "%commit_msg%"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to commit changes
    pause
    exit /b 1
)

:: Push to remote
echo Pushing to GitHub...
git push -u origin main
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to push
    pause
    exit /b 1
)

echo ===== Push Completed =====
pause 