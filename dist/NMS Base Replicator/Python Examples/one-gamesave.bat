@echo off
setlocal DisableDelayedExpansion
if "%~4"=="" goto usage
if not "%~5"=="" goto usage
if not defined NMS_PYTHON set "NMS_PYTHON=python"
"%NMS_PYTHON%" "%~dp0main.py" replicate --source "%~1" --source-base "%~2" --destination "%~1" --destination-base "%~3" --output-prefix "%~4"
exit /b %errorlevel%

:usage
echo Usage: %~nx0 "<gamesave.json>" "<source base name or number>" "<destination base name or number>" "<new output prefix>"
exit /b 2
