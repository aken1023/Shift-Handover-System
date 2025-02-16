@echo off
chcp 65001
echo ===== Cleaning sensitive data =====

:: Remove files from git history
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch __pycache__/*.pyc" --prune-empty --tag-name-filter cat -- --all
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch blueprints/care_record/__pycache__/*.pyc" --prune-empty --tag-name-filter cat -- --all

:: Remove the old refs
git for-each-ref --format="delete %(refname)" refs/original/ | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ===== Cleaning completed =====
pause 