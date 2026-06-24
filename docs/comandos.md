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

### Terminal 3: Operador (curl)

```bash
# Usar comandos curl para interactuar con el C2
```

---

## Endpoints Disponibles

### Información del Servidor (sin auth)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Info del C2 (nombre, NONCE, endpoints) |
| GET | `/health` | Healthcheck del servidor |

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
| `C2_LOG_FILE` | `c2.log` | Archivo de log |

### Implant

| Variable | Default | Descripción |
|----------|---------|-------------|
| `C2_URL` | `http://127.0.0.1:8080` | URL del servidor C2 |
| `C2_AUTH_TOKEN` | `supersecret-ctf-token` | Token de autenticación |
| `C2_HEARTBEAT_INTERVAL` | `30` | Intervalo de heartbeat (segundos) |
| `C2_COMMAND_TIMEOUT` | `15` | Timeout de ejecución (segundos) |

---

## Flujo de Ejecución

```
1. Servidor arranca → Listening en :8080
2. Implant se conecta → POST /register → Obtiene agent_id
3. Loop cada 30 segundos:
   a. Implant → POST /heartbeat → Servidor responde "ok"
   b. Implant → GET /task/{id} → ¿Hay tarea?
   c. Si hay tarea:
      - Implant ejecuta comando (whitelist)
      - Implant → POST /result/{id} → Envía resultado
4. Operador consulta resultados → GET /results/{id}
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

# 6. Esperar 30 segundos (ciclo del implant)

# 7. Ver resultado
curl -H "X-Auth-Token: supersecret-ctf-token" \
  http://127.0.0.1:8080/results/$AGENT_ID

# 8. Detener sistema
./stop.sh
```
