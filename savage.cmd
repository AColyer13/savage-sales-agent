@echo off
REM Savage Sales Agent launcher (Windows).
REM First run: checks your computer and starts guided setup. After that: opens the agent.
REM One-shot use still works after setup:  savage -p "/objection ..."
cd /d "%~dp0"
if "%~1"=="" goto interactive
if exist .savage_setup_done goto passthrough
:interactive
where python >nul 2>nul && (python setup.py --launch & goto :eof)
where py >nul 2>nul && (py setup.py --launch & goto :eof)
echo Python is not installed. Get it from https://www.python.org/downloads/ then run savage.cmd again.
goto :eof
:passthrough
claude %*
