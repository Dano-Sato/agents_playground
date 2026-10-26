@echo off
chcp 65001 >nul
cd /d "%~dp0"
title agent_playground wiki
set PYTHONIOENCODING=utf-8

where python >nul 2>nul
if %errorlevel%==0 (
    python "_wiki\server.py" %*
) else (
    py "_wiki\server.py" %*
)

if errorlevel 1 pause
