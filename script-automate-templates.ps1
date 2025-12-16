# -----------------------------
# Script para lanzar la GUI desde la raíz del proyecto
# -----------------------------

# Obtener la carpeta raíz del proyecto (donde está este script)
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Ruta a src
$SrcDir = Join-Path $RootDir "python_app\src"

# Navegar a src
Set-Location $SrcDir

# -----------------------------
# Detectar Python dinámicamente
# -----------------------------
$PythonExe = $null

# 1. Intentar usar Python del PATH
try {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
} catch {
    Write-Host "Python no está en el PATH, buscando rutas comunes..."
}

# 2. Si no se encontró, intentar ruta por defecto de instalación local
if (-not $PythonExe) {
    $DefaultPath = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
    if (Test-Path $DefaultPath) {
        $PythonExe = $DefaultPath
    } else {
        Write-Error "No se pudo encontrar Python. Instálalo o añade Python al PATH."
        exit 1
    }
}

Write-Host "Usando Python en: $PythonExe"

# -----------------------------
# Ejecutar main.py como módulo
# -----------------------------
& $PythonExe -m main

# -----------------------------
# Esperar a que el usuario presione Enter antes de cerrar
# -----------------------------
Write-Host "`nPresiona Enter para salir..."
Read-Host

