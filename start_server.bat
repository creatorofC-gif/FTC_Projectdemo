@echo off
echo ========================================
echo Fintech Stock Simulator Server
echo ========================================
echo.
echo Starting server...
echo.
echo Once server starts, your browser will open automatically!
echo.
echo Server will be available at: http://127.0.0.1:8000/
echo.
echo Press CTRL+C to stop the server
echo.
echo ========================================
echo.

REM Wait a moment for server to start, then open browser
start "" "http://127.0.0.1:8000/"

REM Start the server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

pause
