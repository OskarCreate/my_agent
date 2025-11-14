# Script para reiniciar el servidor del agente limpiamente

Write-Host "Deteniendo procesos en puerto 8000..." -ForegroundColor Yellow

# Obtener todos los PIDs que escuchan en puerto 8000
$processIds = netstat -ano | Select-String ":8000.*LISTENING" | ForEach-Object {
    if ($_ -match "\s+(\d+)\s*$") {
        $matches[1]
    }
} | Sort-Object -Unique

if ($processIds) {
    foreach ($processId in $processIds) {
        try {
            Write-Host "Deteniendo proceso $processId..." -ForegroundColor Cyan
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "No se pudo detener proceso $processId" -ForegroundColor Red
        }
    }
    Start-Sleep -Seconds 2
    Write-Host "Procesos detenidos." -ForegroundColor Green
} else {
    Write-Host "No hay procesos en puerto 8000." -ForegroundColor Green
}

# Iniciar el servidor del agente
Write-Host "`nIniciando servidor del agente..." -ForegroundColor Yellow
Write-Host "Asegúrate de que el entorno virtual esté activado (.venv\Scripts\Activate.ps1)" -ForegroundColor Magenta
Write-Host "`nEjecuta manualmente:" -ForegroundColor White
Write-Host "  cd 'C:\agentes de ia\agente2\my_agent'" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  uvicorn api.main:app --reload --port 8000" -ForegroundColor Cyan
