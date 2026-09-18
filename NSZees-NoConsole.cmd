@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON_EXE=%ROOT%bin\python.exe"
set "LAUNCHER=%ROOT%launcher.py"

if not exist "%LAUNCHER%" (
    echo [NSZees] Missing launcher: %LAUNCHER%
    echo Ensure launcher.py is included in this distribution.
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo [NSZees] Missing runtime: %PYTHON_EXE%
    echo Ensure the full /bin folder is included in this distribution.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%LAUNCHER%"
endlocal
exit /b 0