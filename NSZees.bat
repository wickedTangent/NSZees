@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON_EXE=%ROOT%bin\python.exe"
set "ENTRYPOINT=%ROOT%run_nszees.py"

if not exist "%PYTHON_EXE%" (
    echo [NSZees] Missing runtime: %PYTHON_EXE%
    echo Ensure the full /bin folder is included in this distribution.
    pause
    exit /b 1
)

if not exist "%ENTRYPOINT%" (
    echo [NSZees] Missing entrypoint: %ENTRYPOINT%
    echo Ensure run_nszees.py is included in this distribution.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%ENTRYPOINT%"
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo [NSZees] Exited with code %APP_EXIT%.
    pause
)

endlocal
exit /b %APP_EXIT%