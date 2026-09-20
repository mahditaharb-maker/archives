@echo off
set "PYDIR=D:\Python3.8.9"

reg add "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "%PATH%;%PYDIR%;%PYDIR%\Scripts" /f

set "PATH=%PATH%;%PYDIR%;%PYDIR%\Scripts"

echo Done. PATH updated in this window.
echo.
python --version
pip --version
cd \
cmd