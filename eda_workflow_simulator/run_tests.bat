@echo off
REM Runs the full unittest suite.
cd /d "%~dp0"
set "PYEXE=py"
set "PYARGS=-3"
if exist ".venv\Scripts\python.exe" (set "PYEXE=%CD%\.venv\Scripts\python.exe" & set "PYARGS=")
"%PYEXE%" %PYARGS% -m unittest discover -s tests -t . -v
exit /b %ERRORLEVEL%
