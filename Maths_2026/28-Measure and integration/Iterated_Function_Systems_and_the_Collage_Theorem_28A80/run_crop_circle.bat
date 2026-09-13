@echo off
setlocal EnableDelayedExpansion
title Crop Circle Generator - Launcher

:: ============================================================
:: CONFIG
:: ============================================================
set "SCRIPT=crop_circle_generator.py"
set "OUTDIR=output"
set "PY=python"

:: Python 3.8-compatible pins. Unpin if you upgrade Python.
set "NUMPY_SPEC=numpy==1.24.4"
set "MPL_SPEC=matplotlib==3.7.5"
set "SCIPY_SPEC=scipy==1.10.1"

:: ============================================================
:: HEADER
:: ============================================================
cls
echo ============================================================
echo   CROP CIRCLE GENERATOR  (IFS + Collage Theorem)
echo ============================================================
echo.

:: ============================================================
:: STEP 1 - CHECK PYTHON
:: ============================================================
echo [1/5] Checking Python installation...
where %PY% >nul 2>nul
if errorlevel 1 goto no_python

for /f "tokens=2 delims= " %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo       Python %PYVER% detected.
echo.

:: ============================================================
:: STEP 2 - UPGRADE PIP
:: ============================================================
echo [2/5] Upgrading pip...
%PY% -m pip install --upgrade pip --quiet --disable-pip-version-check --no-warn-script-location >nul 2>nul
echo       pip step finished.
echo.

:: ============================================================
:: STEP 3 - INSTALL PACKAGES
:: ============================================================
echo [3/5] Installing required packages...
echo.

echo       Checking numpy...
%PY% -c "import numpy" >nul 2>nul
if errorlevel 1 goto install_numpy
echo       numpy already installed.
goto check_matplotlib

:install_numpy
echo       Installing %NUMPY_SPEC%...
%PY% -m pip install "%NUMPY_SPEC%" --quiet --disable-pip-version-check --no-warn-script-location
if errorlevel 1 goto pip_failed
echo       numpy installed.
goto check_matplotlib

:check_matplotlib
echo.
echo       Checking matplotlib...
%PY% -c "import matplotlib" >nul 2>nul
if errorlevel 1 goto install_mpl
echo       matplotlib already installed.
goto check_scipy

:install_mpl
echo       Installing %MPL_SPEC%...
%PY% -m pip install "%MPL_SPEC%" --quiet --disable-pip-version-check --no-warn-script-location
if errorlevel 1 goto pip_failed
echo       matplotlib installed.
goto check_scipy

:check_scipy
echo.
echo       Checking scipy (optional)...
%PY% -c "import scipy" >nul 2>nul
if errorlevel 1 goto install_scipy
echo       scipy already installed.
goto packages_done

:install_scipy
echo       Installing %SCIPY_SPEC%...
%PY% -m pip install "%SCIPY_SPEC%" --quiet --disable-pip-version-check --no-warn-script-location
if errorlevel 1 goto scipy_warn
echo       scipy installed.
goto packages_done

:scipy_warn
echo       WARNING: scipy install failed. collage_fit will be unavailable.
goto packages_done

:packages_done
echo.
echo       All packages ready.
echo.
goto check_script

:: ============================================================
:: ERROR HANDLERS
:: ============================================================
:no_python
echo.
echo   ERROR: Python not found in PATH.
echo   Install Python 3.8+ from https://www.python.org/downloads/
echo   Make sure to tick "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:pip_failed
echo.
echo   ERROR: pip install failed.
echo   Try manually:
echo       %PY% -m pip install %NUMPY_SPEC%
echo       %PY% -m pip install %MPL_SPEC%
echo.
pause
exit /b 1

:: ============================================================
:: STEP 4 - CHECK SCRIPT
:: ============================================================
:check_script
if not exist "%SCRIPT%" goto no_script
goto menu

:no_script
echo   ERROR: %SCRIPT% not found in current directory.
echo   Place this .bat file next to crop_circle_generator.py.
echo.
pause
exit /b 1

:: ============================================================
:: STEP 5 - USER PARAMETERS
:: ============================================================
:menu
echo ============================================================
echo   PARAMETERS
echo ============================================================
echo.
echo   Available presets:
echo     1 = rosette            (n-fold symmetric rosette)
echo     2 = rosette_dihedral   (full D_n symmetry)
echo     3 = rings_spiral       (concentric rings + spiral)
echo     4 = fractal_tree       (binary self-similar tree)
echo     5 = dragon             (Heighway dragon)
echo     6 = sierpinski         (Sierpinski triangle, filled)
echo     7 = prime_gap          (rosette from prime gaps)
echo     8 = prime_value        (rosette from sqrt(p))
echo     9 = prime_residue      (rosette from p mod q)
echo     0 = all                (generate every preset)
echo.

:ask_preset
set "PRESET="
set /p "PRESET=Enter preset number or name [default: 1]: "
if "%PRESET%"=="" set "PRESET=1"

if "%PRESET%"=="1" set "PRESET=rosette"
if "%PRESET%"=="2" set "PRESET=rosette_dihedral"
if "%PRESET%"=="3" set "PRESET=rings_spiral"
if "%PRESET%"=="4" set "PRESET=fractal_tree"
if "%PRESET%"=="5" set "PRESET=dragon"
if "%PRESET%"=="6" set "PRESET=sierpinski"
if "%PRESET%"=="7" set "PRESET=prime_gap"
if "%PRESET%"=="8" set "PRESET=prime_value"
if "%PRESET%"=="9" set "PRESET=prime_residue"
if "%PRESET%"=="0" set "PRESET=all"

set "VALID=0"
for %%P in (rosette rosette_dihedral rings_spiral fractal_tree dragon sierpinski prime_gap prime_value prime_residue all) do (
    if /i "%PRESET%"=="%%P" set "VALID=1"
)
if "%VALID%"=="0" goto bad_preset
echo       Selected preset: %PRESET%
echo.
goto ask_n

:bad_preset
echo       Invalid preset: %PRESET%
goto ask_preset

:ask_n
set "N="
set /p "N=Symmetry order n [default: 12]: "
if "%N%"=="" set "N=12"
echo %N%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 goto bad_n
if %N% LSS 2 goto bad_n_range
if %N% GTR 128 goto bad_n_range
echo       Symmetry order: %N%
echo.
goto ask_depth

:bad_n
echo       Invalid number. Try again.
goto ask_n

:bad_n_range
echo       n must be between 2 and 128.
goto ask_n

:ask_depth
set "DEPTH="
set /p "DEPTH=Iteration depth [default: 6]: "
if "%DEPTH%"=="" set "DEPTH=6"
echo %DEPTH%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 goto bad_depth
if %DEPTH% LSS 1 goto bad_depth_range
if %DEPTH% GTR 20 goto bad_depth_range
echo       Iteration depth: %DEPTH%
echo.
goto ask_cap

:bad_depth
echo       Invalid number. Try again.
goto ask_depth

:bad_depth_range
echo       depth must be between 1 and 20.
goto ask_depth

:ask_cap
echo.
echo   Point-count cap (larger = more detail, more RAM):
echo     1 = 500,000     (~8 MB)
echo     2 = 2,000,000   (~32 MB)
echo     3 = 4,000,000   (recommended, ~64 MB)
echo     4 = 10,000,000  (~160 MB)
echo     5 = 30,000,000  (~480 MB)
echo.
set "CAPCH="
set /p "CAPCH=Choose [1-5, default 3]: "
if "%CAPCH%"=="" set "CAPCH=3"
if "%CAPCH%"=="1" set "MAXP=500000"
if "%CAPCH%"=="2" set "MAXP=2000000"
if "%CAPCH%"=="3" set "MAXP=4000000"
if "%CAPCH%"=="4" set "MAXP=10000000"
if "%CAPCH%"=="5" set "MAXP=30000000"
if not defined MAXP goto bad_cap
echo       Point cap: %MAXP%
echo.
goto ask_outdir

:bad_cap
echo       Invalid choice.
goto ask_cap

:ask_outdir
set "USEROUT="
set /p "USEROUT=Output folder [default: %OUTDIR%]: "
if "%USEROUT%"=="" set "USEROUT=%OUTDIR%"
echo       Output folder: %USEROUT%
echo.

:: ============================================================
:: STEP 6 - CONFIRM
:: ============================================================
echo ============================================================
echo   SUMMARY
echo ============================================================
echo   Preset         : %PRESET%
echo   Symmetry order : %N%
echo   Depth          : %DEPTH%
echo   Point cap      : %MAXP%
echo   Output folder  : %USEROUT%
echo ============================================================
echo.

set "CONFIRM="
set /p "CONFIRM=Proceed? [Y/n]: "
if /i "%CONFIRM%"=="n" goto aborted

:: ============================================================
:: STEP 7 - RUN
:: ============================================================
if not exist "%USEROUT%" mkdir "%USEROUT%"

echo.
echo [4/5] Generating crop circles...
echo.
%PY% "%SCRIPT%" --preset %PRESET% --n %N% --depth %DEPTH% --outdir "%USEROUT%" --max-points %MAXP%
if errorlevel 1 goto gen_failed

echo.
echo [5/5] Done.
echo ============================================================
echo   OUTPUT: %USEROUT%\
echo ============================================================
echo.
dir /b "%USEROUT%\*.png" 2>nul
echo.
echo Opening output folder...
start "" "%USEROUT%"
echo.
pause
endlocal
exit /b 0

:aborted
echo Aborted.
pause
exit /b 0

:gen_failed
echo.
echo   ERROR: generation failed. See messages above.
echo.
pause
exit /b 1