@echo off
cd /d "%~dp0"
py -3 report_cli.py %*
pause
