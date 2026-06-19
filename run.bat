@echo off
REM Avvio dell'app DOPAMINIC
cd /d "%~dp0"
if exist env\Scripts\python.exe (
    env\Scripts\python.exe app.py
) else (
    python app.py
)
