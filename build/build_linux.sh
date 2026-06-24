#!/bin/bash
# =============================================================================
# C2 CTF SecOpsDays - Build Script para Implant Linux
# =============================================================================
# Compila el implant Python a un binario standalone usando PyInstaller
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
echo "  ║  C2 CTF SecOpsDays - Linux Implant Builder       ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar PyInstaller
echo -e "${YELLOW}[1/3] Verificando PyInstaller...${NC}"
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${RED}Error: PyInstaller no encontrado${NC}"
    echo "Instalar con: pip install pyinstaller"
    exit 1
fi
echo -e "${GREEN}   ✓ PyInstaller encontrado${NC}"

# Verificar dependencias del implant
echo -e "${YELLOW}[2/3] Verificando dependencias...${NC}"
cd "$ROOT_DIR"
pip install -r implant/requirements.txt --quiet
echo -e "${GREEN}   ✓ Dependencias instaladas${NC}"

# Compilar implant
echo -e "${YELLOW}[3/3] Compilando implant Linux...${NC}"
cd "$IMPLANT_DIR"

pyinstaller \
    --onefile \
    --strip \
    --name implant-linux \
    --distpath "$BUILD_DIR" \
    --add-data "../profiles/default.yaml:profiles" \
    --hidden-import yaml \
    --clean \
    --noconfirm \
    implant.py

# Verificar resultado
if [ -f "$BUILD_DIR/implant-linux" ]; then
    chmod +x "$BUILD_DIR/implant-linux"
    SIZE=$(du -h "$BUILD_DIR/implant-linux" | cut -f1)
    echo ""
    echo -e "${GREEN}  ✓ Build exitoso${NC}"
    echo -e "  → Archivo: ${BUILD_DIR}/implant-linux"
    echo -e "  → Tamaño:  ${SIZE}"
    echo ""
else
    echo -e "${RED}  ✗ Build falló${NC}"
    exit 1
fi
