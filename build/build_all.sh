#!/bin/bash
# =============================================================================
# C2 CTF SecOpsDays - Build Script para ambos platforms
# =============================================================================
# Compila el implant para Linux y Windows
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

echo -e "${BLUE}"
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║  C2 CTF SecOpsDays - Build All Platforms         ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Build Linux
echo -e "${YELLOW}=== Building Linux Implant ===${NC}"
bash "$SCRIPT_DIR/build_linux.sh"

echo ""

# Build Windows
echo -e "${YELLOW}=== Building Windows Implant ===${NC}"
bash "$SCRIPT_DIR/build_windows.sh"

echo ""

# Resumen
echo -e "${BLUE}=== Build Summary ===${NC}"
echo -e "Archivos generados en: ${ROOT_DIR}/dist/"
ls -lh "$ROOT_DIR/dist/" 2>/dev/null || echo "  (no hay archivos)"
echo ""
