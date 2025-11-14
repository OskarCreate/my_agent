#!/usr/bin/env pwsh
# Script para iniciar el servidor del agente de viajes

Write-Host "Iniciando servidor del agente en puerto 8000..." -ForegroundColor Green

# Cambiar al directorio del agente
Set-Location "C:\agentes de ia\agente2\my_agent"

# Activar entorno virtual
& ".\.venv\Scripts\Activate.ps1"

# Iniciar servidor con uvicorn
Write-Host "Servidor corriendo en http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Presiona Ctrl+C para detener" -ForegroundColor Yellow
uvicorn api.main:app --reload --port 8000
