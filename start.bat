@echo off
cd /d "%~dp0"
echo Aview_MES 1.0 Launcher
".venv\Scripts\python.exe" manage.py runserver 0.0.0.0:9000 --noreload
pause
