@echo off
setlocal DisableDelayedExpansion
if "%~4"=="" goto usage
if not "%~5"=="" goto usage
if not defined NMS_PYTHON set "NMS_PYTHON=python"
"%NMS_PYTHON%" "%~dp0main.py" replicate --source "%~1" --destination "%~2" --destination-base "%~3" --output-prefix "%~4"
exit /b %errorlevel%

:usage
echo Usage: %~nx0 "<source.nmsbase>" "<destination.json>" "<destination base name or number>" "<new output prefix>"
exit /b 2
