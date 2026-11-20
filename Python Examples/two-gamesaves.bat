@echo off
setlocal DisableDelayedExpansion
if "%~5"=="" goto usage
if not "%~6"=="" goto usage
if not defined NMS_PYTHON set "NMS_PYTHON=python"
"%NMS_PYTHON%" "%~dp0main.py" replicate --source "%~1" --source-base "%~2" --destination "%~3" --destination-base "%~4" --output-prefix "%~5"
exit /b %errorlevel%

:usage
echo Usage: %~nx0 "<source.json>" "<source base name or number>" "<destination.json>" "<destination base name or number>" "<new output prefix>"
exit /b 2
