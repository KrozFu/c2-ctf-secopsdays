#!/bin/bash
# =============================================================================
# C2 CTF SecOpsDays - Build Script para Implant Windows
# =============================================================================
# Compila el implant Python a un .exe usando PyInstaller + Wine
# Nota: Requiere Wine instalado para cross-compilation
# =============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
IMPLANT_DIR="$ROOT_DIR/implant"
BUILD_DIR="$ROOT_DIR/dist"

echo -e "${BLUE}"
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║  C2 CTF SecOpsDays - Windows Implant Builder     ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar PyInstaller
echo -e "${YELLOW}[1/4] Verificando PyInstaller...${NC}"
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${RED}Error: PyInstaller no encontrado${NC}"
    echo "Instalar con: pip install pyinstaller"
    exit 1
fi
echo -e "${GREEN}   ✓ PyInstaller encontrado${NC}"

# Verificar Wine (opcional)
echo -e "${YELLOW}[2/4] Verificando Wine (opcional)...${NC}"
if command -v wine &> /dev/null; then
    if wine python --version &> /dev/null; then
        echo -e "${GREEN}   ✓ Wine + Python encontrados${NC}"
        USE_WINE=true
    else
        echo -e "${RED}   ✗ Wine encontrado pero Python NO está instalado dentro de Wine${NC}"
        echo -e "${YELLOW}   Instalar Python en Wine:${NC}"
        echo -e "${YELLOW}     1. Descarga python-3.11.x-amd64.exe desde python.org${NC}"
        echo -e "${YELLOW}     2. wine python-3.11.x-amd64.exe${NC}"
        echo -e "${YELLOW}     3. wine pip install pyinstaller pyyaml requests${NC}"
        echo -e "${YELLOW}   O usa build_windows_native.ps1 directamente en Windows${NC}"
        USE_WINE=false
    fi
else
    echo -e "${YELLOW}   ⚠ Wine no encontrado${NC}"
    echo -e "${YELLOW}   Para Windows .exe, usa build_windows_native.ps1 en Windows${NC}"
    USE_WINE=false
fi

# Verificar UPX (opcional)
echo -e "${YELLOW}[2b/4] Verificando UPX...${NC}"
UPX_FLAG=""
if command -v upx &> /dev/null; then
    UPX_DIR="$(dirname "$(which upx)")"
    echo -e "${GREEN}   ✓ UPX encontrado → compresión activada (~60% reducción)${NC}"
    UPX_FLAG="--upx-dir=${UPX_DIR}"
else
    echo -e "${YELLOW}   ⚠ UPX no encontrado → binario sin comprimir${NC}"
    echo -e "${YELLOW}     Instalar: sudo pacman -S upx  /  sudo apt install upx-ucl${NC}"
fi

# Verificar icono (opcional)
ICON_FLAG=""
ICON_PATH="$SCRIPT_DIR/assets/implant.ico"
if [ -f "$ICON_PATH" ]; then
    echo -e "${GREEN}   ✓ Icono encontrado: $ICON_PATH${NC}"
    ICON_FLAG="--icon=$ICON_PATH"
fi

# Verificar dependencias del implant
echo -e "${YELLOW}[3/4] Verificando dependencias...${NC}"
cd "$ROOT_DIR"
pip install -r implant/requirements.txt --quiet
echo -e "${GREEN}   ✓ Dependencias instaladas${NC}"

# Compilar implant para Windows (si Wine disponible)
echo -e "${YELLOW}[4/4] Compilando implant Windows...${NC}"
cd "$IMPLANT_DIR"

if [ "$USE_WINE" = true ]; then
    wine python -m PyInstaller \
        --onefile \
        --noconsole \
        --name implant.exe \
        --distpath "$BUILD_DIR" \
        --add-data "../profiles/default.yaml;profiles" \
        --hidden-import yaml \
        --clean \
        --noconfirm \
        ${UPX_FLAG} \
        ${ICON_FLAG} \
        implant.py

    if [ -f "$BUILD_DIR/implant.exe" ]; then
        SIZE=$(du -h "$BUILD_DIR/implant.exe" | cut -f1)
        echo ""
        echo -e "${GREEN}  ✓ Build Windows exitoso${NC}"
        echo -e "  → Archivo: ${BUILD_DIR}/implant.exe"
        echo -e "  → Tamaño:  ${SIZE}"
        echo -e "  → Modo:    background (sin ventana de consola)"
        echo ""
    else
        echo -e "${RED}  ✗ Cross-compilation falló${NC}"
        echo -e "${YELLOW}  Usa build_windows_native.ps1 en Windows para un build confiable${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ Saltando build Windows${NC}"
    echo -e "${YELLOW}  Opción recomendada: copiar el proyecto a Windows y ejecutar:${NC}"
    echo -e "${YELLOW}    .\\build\\build_windows_native.ps1${NC}"
fi
