@echo off
echo ========================================================
echo   SIH 2026 PS 26171 - PRIVACY BROWSER AGENT RUNNER
echo ========================================================
echo.
set PYTHONPATH=D:\webman

echo [1/3] Starting FastAPI Server on http://127.0.0.1:8080 ...
start "PS26171 Backend Server" cmd /k "C:\Users\cbsai\AppData\Local\Programs\Python\Python313\python.exe -m uvicorn server.app.main:app --host 127.0.0.1 --port 8080"

timeout /t 2 >nul

echo [2/3] Running Automated Privacy & Network Verification ...
C:\Users\cbsai\AppData\Local\Programs\Python\Python313\python.exe tests/privacy/test_network_privacy.py

echo.
echo [3/3] Opening Synthetic Demo Sites in Chrome ...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "D:\webman\demo-sites\bank\index.html" "D:\webman\demo-sites\shop\index.html" "D:\webman\demo-sites\gov-form\index.html"

echo.
echo ========================================================
echo   APPLICATION RUNNING!
echo   1. Backend Server is active on http://127.0.0.1:8080
echo   2. Demo sites opened in Chrome.
echo   3. Load browser-extension in Chrome (chrome://extensions).
echo ========================================================
pause
