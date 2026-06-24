# Project Command and Control (C2 SecOpsDays CTF)

> Este repositorio contiene un servidor C2 y su implant demostrativo creados para el
> **reto SecOpsDays CTF**.

---

## NONCE del equipo (visible en el walkthrough)

```text
TEAM NONCE: sentrysec-2026
```

---

## Estructura del repositorio

```bash
.
├── server/              # Servidor C2 (Flask)
│   ├── app.py
│   ├── routes.py
│   ├── routes_socks.py  # Endpoints SOCKS5
│   ├── models.py
│   ├── config.py
│   ├── listener.py      # Clase Listener
│   ├── socks.py         # Servidor SOCKS5
│   ├── templates/
│   │   └── index.html   # Dashboard HTML
│   ├── static/
│   │   ├── style.css    # Estilos del dashboard
│   │   └── dashboard.js # JS del dashboard
│   └── requirements.txt
├── implant/             # Agente (Python)
│   ├── implant.py
│   ├── modules/
│   │   ├── __init__.py
│   │   └── socks.py     # Cliente SOCKS5
│   └── requirements.txt
├── build/               # Scripts de compilación
│   ├── build_linux.sh   # Build implant Linux
│   ├── build_windows.sh # Build implant Windows
│   └── build_all.sh     # Build ambos
├── profiles/            # Profiles de configuración
│   ├── default.yaml
│   └── example.yaml
├── tests/               # Suite de pruebas (119 tests)
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_routes.py
│   ├── test_implant.py
│   ├── test_security.py
│   ├── test_profiles.py
│   ├── test_jitter.py
│   └── test_new_features.py
├── docs/
│   └── comandos.md      # Guía de comandos
├── start.sh
├── stop.sh
└── README.md
```

---

## Requisitos

- Python >= 3.11
- pip

### Instalación rápida

```bash
# Clonar el repositorio
git clone https://github.com/KrozFu/c2-ctf-secopsdays.git
cd c2-ctf-secopsdays

# Instalar dependencias del servidor
pip install -r server/requirements.txt

# Instalar dependencias del implant
pip install -r implant/requirements.txt
```

---

## Modo de uso

### 1. Levantar el servidor C2

```bash
cd server
python app.py
```

El banner del servidor mostrará el **NONCE** del equipo y los datos de conexión:

```bash
   ____ ____   
  / ___|___ \  
 | |     __) | 
 | |___ / __/  
  \____|_____|

  C2 CTF SecOpsDays — Command & Control
  ------------------------------------------------
  TEAM NONCE : sentrysec-2026
  Listening  : http://0.0.0.0:8080
  Auth token : supersecret-ctf-token
  Heartbeat  : 30s
  ------------------------------------------------
```

> 💡 **Tip:** El `NONCE` aparece tanto en el banner del servidor como en el
> endpoint público `/agents` y en el archivo `server/config.py` como referencia.

### 2. Ejecutar el implant (agente)

En otra terminal (o máquina) apuntando al servidor:

```bash
cd implant
python implant.py
```

El agente registrará su identidad y empezará a enviar heartbeats cada 30 segundos.

### 3. Dashboard visual

Abrir en el navegador:

```
http://127.0.0.1:8080/dashboard
```

El dashboard muestra:
- Lista de agents conectados con status (online/offline)
- Envío de comandos directamente desde la interfaz
- Resultados en tiempo real
- NONCE del equipo visible

### 4. Interactuar con el C2 (comandos operador)

El operador puede encolar tareas y consultar resultados mediante `curl` o cualquier
cliente HTTP.

**Ver agentes conectados:**

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/agents
```

**Enviar una tarea a un agente:**

```bash
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"command": "whoami"}' \
  http://127.0.0.1:8080/task/<AGENT_ID>
```

**Consultar resultados de un agente:**

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/results/<AGENT_ID>
```

---

## Endpoints del servidor

### API Core

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Info del C2 (sin auth) |
| GET | `/health` | Healthcheck sin auth |
| GET | `/dashboard` | Dashboard visual (sin auth) |
| POST | `/register` | Registro del agente |
| POST | `/heartbeat` | Mantenimiento de sesión |
| GET | `/task/<agent_id>` | Obtener tarea pendiente |
| POST | `/task/<agent_id>` | Encolar tarea (operador) |
| POST | `/result/<agent_id>` | Enviar resultado del agente |
| GET | `/agents` | Listar agentes conectados |
| GET | `/results/<agent_id>` | Ver resultados de un agente |

### SOCKS5 Proxy

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/socks/start` | Iniciar servidor SOCKS5 |
| POST | `/socks/stop` | Detener servidor SOCKS5 |
| GET | `/socks/status` | Estado del servidor SOCKS5 |
| GET | `/socks/channels` | Listar canales SOCKS activos |

---

## Seguridad

- **Autenticación** vía header `X-Auth-Token` compartido entre servidor, operador e
  implant.
- **Whitelist de comandos** tanto en el servidor como en el implant (defensa en
  profundidad). Comandos permitidos: `whoami`, `hostname`, `id`, `uname`, `pwd`,
  `ls`, `cat`, `ps`, `env`, `date`, `uptime`, `df`.
- **No se utiliza `shell=True`** en la ejecución de comandos, evitando inyección de
  shell.
- **Rechazo de tokens peligrosos** (`;`, `|`, `&`, `` ` ``, `$(`, `>`, `<`, `\n`).

---

## Variables de entorno

### Servidor

| Variable | Default | Descripción |
|----------|---------|-------------|
| `C2_NONCE` | `sentrysec-2026` | NONCE del equipo (visible en walkthrough) |
| `C2_AUTH_TOKEN` | `supersecret-ctf-token` | Token de autenticación |
| `C2_HOST` | `0.0.0.0` | Bind del servidor |
| `C2_PORT` | `8080` | Puerto de escucha |
| `C2_HEARTBEAT_INTERVAL` | `30` | Intervalo de heartbeat (segundos) |
| `C2_LOG_FILE` | `c2.log` | Archivo de log |

### Implant

| Variable | Default | Descripción |
|----------|---------|-------------|
| `C2_URL` | `http://127.0.0.1:8080` | URL del servidor C2 |
| `C2_AUTH_TOKEN` | `supersecret-ctf-token` | Token de autenticación |
| `C2_HEARTBEAT_INTERVAL` | `30` | Intervalo de heartbeat (segundos) |
| `C2_COMMAND_TIMEOUT` | `15` | Timeout de ejecución (segundos) |

---

## Compilación de Implants

### Requisitos de build

```bash
pip install pyinstaller
```

### Build Linux

```bash
./build/build_linux.sh
# Output: dist/implant-linux
```

### Build Windows

```bash
./build/build_windows.sh
# Output: dist/implant.exe (requiere Wine para cross-compilation)
```

### Build ambos

```bash
./build/build_all.sh
```

### Ejecutar binario standalone

```bash
# Linux
./dist/implant-linux

# Windows
.\dist\implant.exe
```

---

## Pivoting (SOCKS5 Proxy)

El C2 incluye un servidor SOCKS5 para pivoting a través de máquinas comprometidas.

### Iniciar proxy SOCKS

```bash
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"host": "127.0.0.1", "port": 1080}' \
  http://127.0.0.1:8080/socks/start
```

### Usar proxy

```bash
# Con curl
curl --socks5 127.0.0.1:1080 http://target-internal/

# Con SSH
ssh -o ProxyCommand='ncat --proxy-type socks5 --proxy 127.0.0.1:1080 %h %p' user@internal-host
```

### Ver estado

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/socks/status
```

---

## Video walkthrough

> Pendiente: Al finalizar la prueba exitosa del C2 se grabará un video
> walkthrough donde se muestre el banner del servidor con el **NONCE del equipo**
> visible (`sentrysec-2026`).

El video incluirá:

1. Levantamiento del servidor C2 mostrando el banner con el NONCE.
2. Ejecución del implant (agente) conectándose al servidor.
3. Encolado de tareas y recuperación de resultados.
4. Verificación del NONCE en el endpoint `/agents`.

---

## Flujo completo de prueba

### Inicio rápido (automático)

```bash
# Iniciar servidor + implant
./start.sh

# Detener todo
./stop.sh
```

### Prueba manual paso a paso

**1. Iniciar el servidor:**

```bash
cd server
python app.py
```

**2. Verificar que el servidor está corriendo:**

```bash
curl http://127.0.0.1:8080/health
# Respuesta: {"status":"ok"}
```

**3. Ver info del C2 (sin auth):**

```bash
curl http://127.0.0.1:8080/
# Respuesta: {"name":"C2 CTF SecOpsDays","nonce":"sentrysec-2026",...}
```

**4. Iniciar el implant (otra terminal):**

```bash
cd implant
python implant.py
```

**5. Ver agentes conectados:**

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/agents
# Respuesta: {"nonce":"sentrysec-2026","count":1,"agents":[...]}
```

**6. Enviar un comando:**

```bash
# Reemplaza <AGENT_ID> con el ID del paso anterior
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"command": "whoami"}' \
  http://127.0.0.1:8080/task/<AGENT_ID>
```

**7. Ver resultados:**

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/results/<AGENT_ID>
```

### Comandos permitidos (whitelist)

| Comando | Descripción |
|---------|-------------|
| `whoami` | Usuario actual |
| `hostname` | Nombre del host |
| `id` | IDs de usuario/grupo |
| `uname` | Info del sistema operativo |
| `pwd` | Directorio actual |
| `ls` | Listar archivos |
| `cat` | Mostrar contenido de archivo |
| `ps` | Procesos en ejecución |
| `env` | Variables de entorno |
| `date` | Fecha y hora actual |
| `uptime` | Tiempo de actividad |
| `df` | Espacio en disco |

---

## Requerimientos funcionales mínimos

### Servidor (C2 Server)

- Registrar agentes (implants).
- Mantener una lista de agentes conectados.
- Recibir información de los agentes.
- Enviar tareas simples.
- Recibir resultados de tareas.
- Registrar eventos en logs.

### Implant (Agent)

- Generar un identificador único.
- Registrarse en el servidor.
- Enviar heartbeats periódicos.
- Consultar tareas.
- Ejecutar tareas permitidas.
- Enviar resultados.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Operador                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Dashboard  │  │     curl     │  │  SOCKS5      │     │
│  │   (Browser)  │  │   (CLI)      │  │  (Proxy)     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      C2 Server (Flask)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  API Routes  │  │   SOCKS5     │  │  Dashboard   │     │
│  │  (REST)      │  │   Server     │  │  (HTML/CSS)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘     │
│         │                  │                                │
│         ▼                  ▼                                │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │  AgentStore  │  │   Profiles   │                        │
│  │  (in-memory) │  │   (YAML)     │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP (JSON)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Implant (Python)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Heartbeat   │  │   Executor   │  │  SOCKS5      │     │
│  │  (±jitter)   │  │  (whitelist) │  │  Client      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Información recolectada por el implant

```json
{
  "hostname": "client01",
  "os": "Linux 5.15.0",
  "username": "user",
  "ip": "192.168.1.10"
}
```

---

## Diseño del C2

### Servidor

- `app.py`: Configura y levanta el servidor Flask, muestra el banner con el NONCE.
- `routes.py`: Define los endpoints REST y encamina las peticiones.
- `routes_socks.py`: Endpoints para el servicio SOCKS5 proxy.
- `models.py`: Almacena agentes, tareas y resultados en memoria (thread-safe).
- `config.py`: Variables de conexión, NONCE, token y whitelist de comandos.
- `listener.py`: Clase Listener para configuración del servidor.
- `socks.py`: Servidor SOCKS5 para pivoting.

### Dashboard

- `templates/index.html`: Dashboard HTML con auto-refresh.
- `static/style.css`: Estilos CSS (dark theme).
- `static/dashboard.js`: JavaScript para polling de agents.

### Implant

- `implant.py`: Agente que se registra, envía heartbeats y ejecuta comandos.
- `modules/socks.py`: Cliente SOCKS5 para pivoting.

### Configuración

- `profiles/default.yaml`: Profile por defecto (desarrollo/CTF).
- `profiles/example.yaml`: Profile de ejemplo (evasión básica).

### Build

- `build/build_linux.sh`: Compila implant para Linux.
- `build/build_windows.sh`: Compila implant para Windows.
- `build/build_all.sh`: Compila para ambos platforms.

---

## Pruebas

### Ejecutar la suite completa

```bash
python -m pytest tests/ -v
```

### Cobertura de código

```bash
python -m pytest tests/ --cov=. --cov-report=term-missing
```

### Estructura de pruebas

```
tests/
├── conftest.py           # Fixtures compartidos (client Flask, auth headers)
├── test_models.py        # Unitarias: whitelist de comandos, AgentStore, thread-safety
├── test_routes.py        # Integración: todos los endpoints Flask
├── test_implant.py       # Unitarias: whitelist local, generate_id, collect_info
├── test_security.py      # Seguridad: inyección de comandos, auth en todos los endpoints
├── test_profiles.py      # Profiles YAML, Listener class
├── test_jitter.py        # Jitter calculation
└── test_new_features.py  # Dashboard, SOCKS5, módulos
```

### Cobertura por módulo

| Archivo | Pruebas | Qué se valida |
|---------|---------|---------------|
| `models.py` | 14 | Whitelist (12 comandos + args), tokens prohibidos, AgentStore completo, thread-safety |
| `routes.py` | 18 | Health, register, heartbeat, task, result, agents, auth negativa |
| `implant.py` | 7 | Whitelist local, generate_id determinista, collect_info |
| `security.py` | 32 | 16 payloads de inyección × 2 endpoints, auth en 6 endpoints, visibilidad del NONCE |
| `profiles.py` | 15 | Carga YAML, Listener class, valores por defecto |
| `jitter.py` | 6 | Rango de jitter, determinismo, siempre positivo |
| `new_features.py` | 10 | Dashboard HTML, SOCKS5 endpoints, módulos implant |
