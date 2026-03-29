@echo off
echo Starting Medley Player Space...
echo Please wait while we start a local server for the music player.
echo.
npx -y live-server --port=5500 --entry-file=medley.html
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo live-server not found, trying Python server...
    start http://localhost:8000/medley.html
    python -m http.server 8000
)
pause
