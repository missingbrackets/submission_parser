@echo off
title Submission Analyser
echo.
echo  ============================================
echo   Submission Analyser
echo  ============================================
echo.

REM Change to the folder this .bat file lives in
cd /d "%~dp0"

REM Use venv Python and Streamlit directly
SET PYTHON=C:\Git - Repos\submission_analyser\submission_analyser\venv\Scripts\python.exe
SET STREAMLIT=C:\Git - Repos\submission_analyser\submission_analyser\venv\Scripts\streamlit.exe

echo  Starting app...
echo  Opening in your browser at http://localhost:8501
echo.
echo  (Close this window to stop the app)
echo.

"%STREAMLIT%" run main.py --server.headless false --browser.gatherUsageStats false

pause
