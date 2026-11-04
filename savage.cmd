@echo off
REM Launch the Savage Sales Agent (CLI). Runs Claude Code inside this folder so CLAUDE.md, playbook/, profile.md and deals/ load.
REM Usage:  savage                      -> interactive session
REM         savage -p "/objection ..."  -> one-shot, prints the answer and exits
cd /d "%~dp0"
claude %*
