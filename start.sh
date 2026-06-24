#!/bin/bash
# =============================================================================
# C2 CTF SecOpsDays - Script de inicio
# Levanta el servidor C2 y el implant en background
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
IMPLANT_DIR="$SCRIPT_DIR/implant"

# Archivos de log y PID
SERVER_PID_FILE="$SCRIPT_DIR/.server.pid"
IMPLANT_PID_FILE="$SCRIPT_DIR/.implant.pid"
SERVER_LOG="$SCRIPT_DIR/server.log"
IMPLANT_LOG="$SCRIPT_DIR/implant.log"

# Puerto del servidor
C2_PORT=${C2_PORT:-8080}

# =============================================================================
# Funciones auxiliares
# =============================================================================

print_banner() {
    echo -e "${BLUE}"
    echo "   ____ ____  "
    echo "  / ___|___ \ "
    echo " | |     __) |"
    echo " | |___ / __/ "
    echo "  \____|_____|"
    echo -e "${NC}"
    echo -e "${GREEN}  C2 CTF SecOpsDays — Script de Inicio${NC}"
    echo ""
}

check_dependencies() {
    echo -e "${YELLOW}[1/4] Verificando dependencias...${NC}"
    
    # Verificar Python
    if ! command -v python &> /dev/null; then
        echo -e "${RED}Error: Python no encontrado${NC}"
        exit 1
    fi
    
    # Verificar Flask
    if ! python -c "import flask" &> /dev/null; then
        echo -e "${RED}Error: Flask no instalado. Ejecuta: pip install -r server/requirements.txt${NC}"
        exit 1
    fi
    
    # Verificar requests
    if ! python -c "import requests" &> /dev/null; then
        echo -e "${RED}Error: requests no instalado. Ejecuta: pip install -r implant/requirements.txt${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}   ✓ Dependencias OK${NC}"
}

stop_existing() {
    echo -e "${YELLOW}[2/4] Deteniendo procesos existentes...${NC}"
    
    # Detener servidor si está corriendo
    if [ -f "$SERVER_PID_FILE" ]; then
        SERVER_PID=$(cat "$SERVER_PID_FILE")
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            kill "$SERVER_PID" 2>/dev/null || true
            echo -e "${GREEN}   ✓ Servidor detenido (PID: $SERVER_PID)${NC}"
        fi
        rm -f "$SERVER_PID_FILE"
    fi
    
    # Detener implant si está corriendo
    if [ -f "$IMPLANT_PID_FILE" ]; then
        IMPLANT_PID=$(cat "$IMPLANT_PID_FILE")
        if kill -0 "$IMPLANT_PID" 2>/dev/null; then
            kill "$IMPLANT_PID" 2>/dev/null || true
            echo -e "${GREEN}   ✓ Implant detenido (PID: $IMPLANT_PID)${NC}"
        fi
        rm -f "$IMPLANT_PID_FILE"
    fi
    
    # Matar procesos en el puerto
    if lsof -ti:$C2_PORT &>/dev/null; then
        echo -e "${YELLOW}   Puerto $C2_PORT en uso, liberando...${NC}"
        kill $(lsof -ti:$C2_PORT) 2>/dev/null || true
        sleep 1
    fi
}

start_server() {
    echo -e "${YELLOW}[3/4] Iniciando servidor C2...${NC}"
    
    python "$SERVER_DIR/app.py" > "$SERVER_LOG" 2>&1 &
    SERVER_PID=$!
    echo "$SERVER_PID" > "$SERVER_PID_FILE"
    
    # Esperar a que el servidor esté listo
    echo -e "${BLUE}   Esperando servidor en puerto $C2_PORT...${NC}"
    for i in {1..30}; do
        if curl -s "http://127.0.0.1:$C2_PORT/health" | grep -q '"status"'; then
            echo -e "${GREEN}   ✓ Servidor listo (PID: $SERVER_PID)${NC}"
            echo -e "${GREEN}   → http://127.0.0.1:$C2_PORT${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}   ✗ Timeout esperando servidor. Revisa $SERVER_LOG${NC}"
    return 1
}

start_implant() {
    echo -e "${YELLOW}[4/4] Iniciando implant...${NC}"
    
    C2_URL="http://127.0.0.1:$C2_PORT" python "$IMPLANT_DIR/implant.py" > "$IMPLANT_LOG" 2>&1 &
    IMPLANT_PID=$!
    echo "$IMPLANT_PID" > "$IMPLANT_PID_FILE"
    
    sleep 2
    
    if kill -0 "$IMPLANT_PID" 2>/dev/null; then
        echo -e "${GREEN}   ✓ Implant iniciado (PID: $IMPLANT_PID)${NC}"
    else
        echo -e "${RED}   ✗ Implant falló al iniciar. Revisa $IMPLANT_LOG${NC}"
        return 1
    fi
}

show_status() {
    echo ""
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${GREEN}  C2 CTF SecOpsDays - Estado${NC}"
    echo -e "${BLUE}=============================================${NC}"
    echo ""
    echo -e "  Servidor:  ${GREEN}http://127.0.0.1:$C2_PORT${NC}"
    echo -e "  Implant:   ${GREEN}PID $IMPLANT_PID${NC}"
    echo -e "  Logs:      $SERVER_LOG, $IMPLANT_LOG"
    echo ""
    echo -e "${YELLOW}  Comandos útiles:${NC}"
    echo "    curl http://127.0.0.1:$C2_PORT/health"
    echo "    curl -H 'X-Auth-Token: supersecret-ctf-token' http://127.0.0.1:$C2_PORT/agents"
    echo ""
    echo -e "${YELLOW}  Para detener:${NC}"
    echo "    ./stop.sh"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

print_banner
check_dependencies
stop_existing
start_server
start_implant
show_status
