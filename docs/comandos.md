# Guía de Comandos - C2 CTF SecOpsDays

## Inicio Rápido

```bash
# Iniciar servidor + implant automáticamente
./start.sh

# Detener todos los servicios
./stop.sh
```

## Inicio Manual (Paso a Paso)

### Terminal 1: Servidor C2

```bash
cd server
python app.py
```

### Terminal 2: Implant (Agente)

```bash
cd implant
python implant.py
```

### Terminal 3: Operador (curl o Dashboard)

```bash
# Opción A: Usar curl
curl -H "X-Auth-Token: supersecret-ctf-token" http://127.0.0.1:8080/agents

# Opción B: Abrir dashboard en navegador
# http://127.0.0.1:8080/dashboard
```

---

## Dashboard Visual

El C2 incluye un dashboard web para interactuar con los agents.

### Abrir Dashboard

```
http://127.0.0.1:8080/dashboard
```

### Funcionalidades

- **Lista de agents** con status (online/offline)
- **Envío de comandos** directamente desde la interfaz
- **Resultados en tiempo real** (auto-refresh cada 5 segundos)
- **NONCE del equipo** visible en el header

### Características del Dashboard

| Feature | Descripción |
|---------|-------------|
| Auto-refresh | Se actualiza cada 5 segundos |
| Sin auth | Accesible sin token para CTF |
| Responsive | Funciona en desktop y móvil |
| Dark theme | Tema oscuro estilo terminal |

---

## Profiles de Configuración

El C2 usa archivos YAML para configurar listeners, agents y operators.

### Profile por defecto

```bash
# Iniciar con profile por defecto
./start.sh

# O especificar manualmente
C2_PROFILE=profiles/default.yaml python server/app.py
```

### Profile de ejemplo (evasión)

```bash
# Iniciar con profile personalizado
C2_PROFILE=profiles/example.yaml ./start.sh
```

### Estructura del Profile

```yaml
listener:
  host: "0.0.0.0"
  port: 8080
  protocol: "http"
  uris:
    - "/register"
    - "/heartbeat"
  headers:
    user_agent: "Mozilla/5.0 ..."
  response:
    server: "nginx/1.24.0"

agent:
  sleep: 30
  jitter: 50          # ±50% → sleep entre 15s y 45s
  timeout: 15
  retry_delay: 5

operators:
  - name: "admin"
    token: "supersecret-ctf-token"
```

### Perfiles disponibles

| Profile | Puerto | Protocolo | Jitter | Uso |
|---------|--------|-----------|--------|-----|
| `default.yaml` | 8080 | HTTP | ±50% | Desarrollo/CTF |
| `example.yaml` | 443 | HTTPS | ±50% | Evasión básica |

---

## Jitter (Aleatorización de Sleep)

El implant usa jitter para evadir detección por patrones de tráfico.

### Configuración

```yaml
agent:
  sleep: 30        # Intervalo base
  jitter: 50       # ±50% → sleep entre 15s y 45s
```

### Ejemplos

| Jitter | Sleep Base | Rango Resultante |
|--------|------------|------------------|
| 20% | 30s | 24s - 36s |
| 50% | 30s | 15s - 45s |
| 100% | 30s | 0s - 60s |

### Override por variable de entorno

```bash
C2_JITTER=20 python implant/implant.py  # Solo 20% de jitter
```

---

## Endpoints Disponibles

### Información del Servidor (sin auth)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Info del C2 (nombre, NONCE, endpoints) |
| GET | `/health` | Healthcheck del servidor |
| GET | `/dashboard` | Dashboard visual |

**Ejemplos:**

```bash
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/health
```

### Endpoints Protegidos (requieren auth)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/register` | Registro de agente |
| POST | `/heartbeat` | Mantenimiento de sesión |
| GET | `/task/<agent_id>` | Obtener tarea pendiente |
| POST | `/task/<agent_id>` | Encolar tarea (operador) |
| POST | `/result/<agent_id>` | Enviar resultado del agente |
| GET | `/agents` | Listar agentes conectados |
| GET | `/results/<agent_id>` | Ver resultados de un agente |

### Endpoints SOCKS5 Proxy

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/socks/start` | Iniciar servidor SOCKS5 |
| POST | `/socks/stop` | Detener servidor SOCKS5 |
| GET | `/socks/status` | Estado del servidor SOCKS5 |
| GET | `/socks/channels` | Listar canales SOCKS activos |

---

## Comandos del Operador

### 1. Verificar Servidor

```bash
curl http://127.0.0.1:8080/health
# Respuesta: {"status":"ok"}
```

### 2. Ver Info del C2

```bash
curl http://127.0.0.1:8080/
# Respuesta: {"name":"C2 CTF SecOpsDays","nonce":"sentrysec-2026",...}
```

### 3. Ver Agentes Conectados

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/agents

# Respuesta:
# {
#   "nonce": "sentrysec-2026",
#   "count": 1,
#   "agents": [
#     {
#       "agent_id": "f4db8711-29b2-54ec-9c6d-adfcdb721b6f",
#       "hostname": "sentrysec",
#       "os": "Linux 7.0.12-1-cachyos",
#       "username": "krozfu",
#       "ip": "192.168.1.121",
#       "status": "online"
#     }
#   ]
# }
```

### 4. Enviar Comando a un Agente

```bash
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"command": "whoami"}' \
  http://127.0.0.1:8080/task/<AGENT_ID>

# Ejemplo completo:
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"command": "whoami"}' \
  http://127.0.0.1:8080/task/f4db8711-29b2-54ec-9c6d-adfcdb721b6f
```

### 5. Ver Resultados

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/results/<AGENT_ID>

# Ejemplo completo:
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/results/f4db8711-29b2-54ec-9c6d-adfcdb721b6f
```

---

## Pivoting (SOCKS5 Proxy)

El C2 incluye un servidor SOCKS5 para pivoting a través de máquinas comprometidas.

### Arquitectura SOCKS

```
[Operador] → localhost:1080 → [Server SOCKS] → C2 Channel → [Implant] → [Target]
```

### Iniciar proxy SOCKS

```bash
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"host": "127.0.0.1", "port": 1080}' \
  http://127.0.0.1:8080/socks/start

# Respuesta:
# {"status":"ok","message":"SOCKS5 server listening on 127.0.0.1:1080"}
```

### Ver estado del proxy

```bash
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/socks/status

# Respuesta:
# {"running":true,"host":"127.0.0.1","port":1080,"channels":0}
```

### Usar proxy con curl

```bash
# Acceder a máquina interna a través del proxy
curl --socks5 127.0.0.1:1080 http://internal-host/

# Con autenticación SOCKS5
curl --socks5 127.0.0.1:1080 --proxy-user user:pass http://target/
```

### Usar proxy con SSH

```bash
# SSH a máquina interna a través del C2
ssh -o ProxyCommand='ncat --proxy-type socks5 --proxy 127.0.0.1:1080 %h %p' user@internal-host
```

### Detener proxy

```bash
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/socks/stop
```

---

## Compilación de Implants

### Requisitos de build

```bash
pip install pyinstaller
```

### Build Linux

```bash
./build/build_linux.sh
# Output: dist/implant-linux (binario standalone)
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

### Crear binario manualmente

```bash
cd implant

# Linux
pyinstaller --onefile --strip --name implant-linux implant.py

# Windows (en Windows o con Wine)
pyinstaller --onefile --name implant.exe implant.py
```

---

## Whitelist de Comandos Permitidos

Solo estos comandos pueden ejecutarse en el agente:

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `whoami` | Usuario actual | `whoami` |
| `hostname` | Nombre del host | `hostname` |
| `id` | IDs de usuario/grupo | `id` |
| `uname` | Info del sistema | `uname -a` |
| `pwd` | Directorio actual | `pwd` |
| `ls` | Listar archivos | `ls -la /tmp` |
| `cat` | Mostrar archivo | `cat /etc/hostname` |
| `ps` | Procesos activos | `ps aux` |
| `env` | Variables de entorno | `env` |
| `date` | Fecha y hora | `date` |
| `uptime` | Tiempo activo | `uptime` |
| `df` | Espacio en disco | `df -h` |

**Comandos RECHAZADOS (por seguridad):**

- `rm`, `wget`, `curl`, `bash`, `python`, `nc`
- Cualquier comando con `;`, `|`, `&`, `` ` ``, `$(`, `>`, `<`

---

## Variables de Entorno

### Servidor

| Variable | Default | Descripción |
|----------|---------|-------------|
| `C2_NONCE` | `sentrysec-2026` | NONCE del equipo |
| `C2_AUTH_TOKEN` | `supersecret-ctf-token` | Token de autenticación |
| `C2_HOST` | `0.0.0.0` | Bind del servidor |
| `C2_PORT` | `8080` | Puerto de escucha |
| `C2_HEARTBEAT_INTERVAL` | `30` | Intervalo de heartbeat (segundos) |
| `C2_PROFILE` | `profiles/default.yaml` | Profile de configuración |
| `C2_LOG_FILE` | `c2.log` | Archivo de log |

### Implant

| Variable | Default | Descripción |
|----------|---------|-------------|
| `C2_URL` | `http://127.0.0.1:8080` | URL del servidor C2 |
| `C2_AUTH_TOKEN` | `supersecret-ctf-token` | Token de autenticación |
| `C2_HEARTBEAT_INTERVAL` | `30` | Intervalo de heartbeat (segundos) |
| `C2_JITTER` | `50` | Porcentaje de jitter (±50%) |
| `C2_COMMAND_TIMEOUT` | `15` | Timeout de ejecución (segundos) |
| `C2_RETRY_DELAY` | `5` | Delay entre reintentos de registro |
| `C2_PROFILE` | `profiles/default.yaml` | Profile de configuración |

---

## Flujo de Ejecución

```
1. Servidor arranca → Listening en :8080
2. Implant se conecta → POST /register → Obtiene agent_id
3. Loop cada 30 segundos (±jitter):
   a. Implant → POST /heartbeat → Servidor responde "ok"
   b. Implant → GET /task/{id} → ¿Hay tarea?
   c. Si hay tarea:
      - Implant ejecuta comando (whitelist)
      - Implant → POST /result/{id} → Envía resultado
4. Operador consulta resultados → GET /results/{id}
5. Dashboard actualiza automáticamente cada 5 segundos
```

---

## Troubleshooting

### El servidor no responde

```bash
# Verificar si está corriendo
lsof -i:8080

# Matar proceso en el puerto
kill $(lsof -ti:8080)

# Reiniciar
./start.sh
```

### El implant no se conecta

```bash
# Verificar que el servidor esté corriendo
curl http://127.0.0.1:8080/health

# Revisar logs del implant
cat implant.log

# Verificar URL del servidor
echo $C2_URL
```

### Errores de autenticación (401)

```bash
# Verificar token
echo $C2_AUTH_TOKEN

# Debe ser: supersecret-ctf-token
```

### Comando rechazado (400)

```bash
# Verificar que el comando esté en la whitelist
# Solo: whoami, hostname, id, uname, pwd, ls, cat, ps, env, date, uptime, df
```

### Dashboard no carga

```bash
# Verificar que los archivos estáticos existan
ls -la server/static/
ls -la server/templates/

# Verificar que Flask sirve estáticos
curl http://127.0.0.1:8080/static/style.css
```

### SOCKS proxy no funciona

```bash
# Verificar estado del proxy
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/socks/status

# Reiniciar proxy
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/socks/stop

curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"host": "127.0.0.1", "port": 1080}' \
  http://127.0.0.1:8080/socks/start
```

---

## Logs

### Servidor

```bash
# Ver logs en tiempo real
tail -f c2.log

# Ver logs del servidor
cat server.log
```

### Implant

```bash
# Ver logs del implant
cat implant.log
```

---

## Ejemplo Completo de Prueba

```bash
# 1. Iniciar sistema
./start.sh

# 2. Verificar servidor (Terminal 3)
curl http://127.0.0.1:8080/health

# 3. Ver agentes conectados
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/agents

# 4. Guardar agent_id de la respuesta anterior
# Ejemplo: AGENT_ID=f4db8711-29b2-54ec-9c6d-adfcdb721b6f

# 5. Enviar comando
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"command": "whoami"}' \
  http://127.0.0.1:8080/task/$AGENT_ID

# 6. Esperar ~30 segundos (ciclo del implant con jitter)

# 7. Ver resultado
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/results/$AGENT_ID

# 8. Abrir dashboard
# http://127.0.0.1:8080/dashboard

# 9. Iniciar SOCKS proxy
curl -X POST -H "X-Auth-Token: supersecret-ctf-token" \
  -H "Content-Type: application/json" \
  -d '{"host": "127.0.0.1", "port": 1080}' \
  http://127.0.0.1:8080/socks/start

# 10. Usar proxy
curl --socks5 127.0.0.1:1080 http://target-internal/

# 11. Detener sistema
./stop.sh
```
