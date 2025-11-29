Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fintech Stock Simulator Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting server..." -ForegroundColor Green
Write-Host ""
Write-Host "Once server starts, your browser will open automatically!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Server will be available at: http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Open browser in background after a short delay
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:8000/"

# Start the server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

