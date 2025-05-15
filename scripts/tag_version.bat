@echo off
setlocal enabledelayedexpansion

set FILE=scripts\..\turinium\__init__.py
for /f "tokens=2 delims=='" %%A in ('findstr __version__ "%FILE%"') do (
    set VERSION=%%A
)

set TAG=v%VERSION%
echo Version: %VERSION%
echo Tag: %TAG%

REM Check if tag already exists
git tag | findstr /x "%TAG%" >nul
if %errorlevel%==0 (
    echo Tag %TAG% already exists. Skipping.
) else (
    git tag %TAG%
    git push origin %TAG%
    echo Tag %TAG% created and pushed!
)