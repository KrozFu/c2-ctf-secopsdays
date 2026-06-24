#!/bin/bash
# =============================================================================
# C2 CTF SecOpsDays - Script de parada
# Detiene el servidor C2 y el implant
# =============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PID_FILE="$SCRIPT_DIR/.server.pid"
IMPLANT_PID_FILE="$SCRIPT_DIR/.implant.pid"

# Puerto del servidor
C2_PORT=${C2_PORT:-8080}

echo -e "${BLUE}"
echo "   ____ ____  "
echo "  / ___|___ \ "
echo " | |     __) |"
echo " | |___ / __/ "
echo "  \____|_____|"
echo -e "${NC}"
echo -e "${RED}  C2 CTF SecOpsDays — Deteniendo servicios${NC}"
echo ""

# Detener implant
if [ -f "$IMPLANT_PID_FILE" ]; then
    IMPLANT_PID=$(cat "$IMPLANT_PID_FILE")
    if kill -0 "$IMPLANT_PID" 2>/dev/null; then
        kill "$IMPLANT_PID" 2>/dev/null || true
        echo -e "${GREEN}✓ Implant detenido (PID: $IMPLANT_PID)${NC}"
    else
        echo -e "${YELLOW}⚠ Implant ya no estaba corriendo${NC}"
    fi
    rm -f "$IMPLANT_PID_FILE"
else
    echo -e "${YELLOW}⚠ No se encontró archivo PID del implant${NC}"
fi

# Detener servidor
if [ -f "$SERVER_PID_FILE" ]; then
    SERVER_PID=$(cat "$SERVER_PID_FILE")
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        echo -e "${GREEN}✓ Servidor detenido (PID: $SERVER_PID)${NC}"
    else
        echo -e "${YELLOW}⚠ Servidor ya no estaba corriendo${NC}"
    fi
    rm -f "$SERVER_PID_FILE"
else
    echo -e "${YELLOW}⚠ No se encontró archivo PID del servidor${NC}"
fi

# Limpiar procesos en el puerto
if lsof -ti:$C2_PORT &>/dev/null; then
    echo -e "${YELLOW}Limpiando procesos en puerto $C2_PORT...${NC}"
    kill $(lsof -ti:$C2_PORT) 2>/dev/null || true
    sleep 1
fi

echo ""
echo -e "${GREEN}✓ Todos los servicios detenidos${NC}"
echo ""
