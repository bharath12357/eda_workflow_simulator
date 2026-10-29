@echo off
REM Runs a passing demo, then several deliberate-failure demos.
cd /d "%~dp0"
set "PYEXE=py"
set "PYARGS=-3"
if exist ".venv\Scripts\python.exe" (set "PYEXE=%CD%\.venv\Scripts\python.exe" & set "PYARGS=")

echo ===== 1. List stages =====
"%PYEXE%" %PYARGS% -m eda_sim list-stages

echo.
echo ===== 2. Successful run: counter.v =====
"%PYEXE%" %PYARGS% -m eda_sim run sample_inputs\counter.v

echo.
echo ===== 3. Successful run: alu.v (two modules, one instance) =====
"%PYEXE%" %PYARGS% -m eda_sim run sample_inputs\alu.v

echo.
echo ===== 4. Expected failure: unbalanced module =====
"%PYEXE%" %PYARGS% -m eda_sim run sample_inputs\broken_unbalanced.v --delay-ms 0

echo.
echo ===== 5. Injected timeout, recovered by retry =====
"%PYEXE%" %PYARGS% -m eda_sim run sample_inputs\counter.v --inject-failure simulation --failure-mode timeout

echo.
echo ===== 6. Injected crash =====
"%PYEXE%" %PYARGS% -m eda_sim run sample_inputs\counter.v --inject-failure lint --failure-mode crash --delay-ms 0

echo.
echo Demo finished. JSON reports are in the reports folder; logs are in the logs folder.
exit /b 0
