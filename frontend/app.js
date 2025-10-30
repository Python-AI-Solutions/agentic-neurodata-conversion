// Configuration
const API_BASE_URL = 'http://localhost:8000';
let activeSessions = new Map();
let currentSessionId = null;

// Initialize app on load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
});

// App initialization
async function initializeApp() {
    addSystemMessage('Initializing connection to MCP server...');
    await checkHealth();
    await refreshSessions();
    setInterval(checkHealth, 10000); // Check health every 10 seconds
}

// Event listeners
function setupEventListeners() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendButton.addEventListener('click', sendMessage);
}

// Health check
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();

        // Update status indicator
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');

        if (data.status === 'healthy') {
            statusDot.classList.add('connected');
            statusDot.classList.remove('error');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusDot.classList.add('error');
            statusText.textContent = 'Unhealthy';
        }

        // Update sidebar stats
        document.getElementById('mcpStatus').textContent = data.status;
        document.getElementById('mcpStatus').className = `stat-value ${data.status === 'healthy' ? 'success' : 'error'}`;

        document.getElementById('redisStatus').textContent = data.redis_connected ? 'Connected' : 'Disconnected';
        document.getElementById('redisStatus').className = `stat-value ${data.redis_connected ? 'success' : 'error'}`;

        document.getElementById('agentsStatus').textContent = `${data.agents_registered.length}/3`;
        document.getElementById('agentsStatus').className = `stat-value ${data.agents_registered.length === 3 ? 'success' : 'error'}`;

        return data;
    } catch (error) {
        console.error('Health check failed:', error);

        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        statusDot.classList.remove('connected');
        statusDot.classList.add('error');
        statusText.textContent = 'Connection Error';

        document.getElementById('mcpStatus').textContent = 'Error';
        document.getElementById('mcpStatus').className = 'stat-value error';
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // Clear input and disable send button
    input.value = '';
    const sendButton = document.getElementById('sendButton');
    sendButton.disabled = true;

    // Add user message to chat
    addUserMessage(message);

    // Show loading indicator
    showLoading();

    // Process command
    try {
        await processCommand(message);
    } catch (error) {
        addAssistantMessage(`Error: ${error.message}`);
    } finally {
        hideLoading();
        sendButton.disabled = false;
        input.focus();
    }
}

// Process user commands
async function processCommand(message) {
    const lowerMessage = message.toLowerCase().trim();

    // Help command
    if (lowerMessage === 'help') {
        showHelpMessage();
        return;
    }

    // Start conversion command
    if (lowerMessage.startsWith('start conversion') || lowerMessage.startsWith('convert')) {
        const pathMatch = message.match(/(?:start conversion|convert)\s+(.+)/i);
        if (pathMatch) {
            await startConversion(pathMatch[1].trim());
        } else {
            addAssistantMessage('Please specify a dataset path. Example: `start conversion ./tests/data/synthetic_openephys`');
        }
        return;
    }

    // Check status command
    if (lowerMessage.startsWith('check status') || lowerMessage.startsWith('status')) {
        const sessionMatch = message.match(/(?:check status|status)\s+(.+)/i);
        if (sessionMatch) {
            await checkSessionStatus(sessionMatch[1].trim());
        } else if (currentSessionId) {
            await checkSessionStatus(currentSessionId);
        } else {
            addAssistantMessage('Please specify a session ID or start a conversion first.');
        }
        return;
    }

    // List sessions command
    if (lowerMessage === 'list sessions' || lowerMessage === 'sessions') {
        await refreshSessions();
        addAssistantMessage(`Found ${activeSessions.size} active session(s). Check the sidebar for details.`);
        return;
    }

    // Check health command
    if (lowerMessage === 'health' || lowerMessage === 'check health') {
        const health = await checkHealth();
        if (health) {
            addAssistantMessage(`System is ${health.status}. ${health.agents_registered.length} agents registered. Redis: ${health.redis_connected ? 'connected' : 'disconnected'}.`);
        }
        return;
    }

    // Default response for unrecognized commands
    addAssistantMessage('I didn\'t understand that command. Type `help` to see available commands.');
}

// Start a new conversion
async function startConversion(datasetPath) {
    try {
        addAssistantMessage(`Starting conversion for dataset: ${datasetPath}...`);

        const response = await fetch(`${API_BASE_URL}/api/v1/sessions/initialize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ dataset_path: datasetPath }),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        currentSessionId = data.session_id;

        addAssistantMessage(`✅ Conversion started successfully!

**Session ID:** \`${data.session_id}\`
**Status:** ${data.workflow_stage}
**Message:** ${data.message}

The conversion is now in progress. Type \`status ${data.session_id}\` to check progress.`);

        // Refresh sessions list
        await refreshSessions();

        // Check for clarification after a short delay
        setTimeout(async () => {
            await checkForClarification(data.session_id);
        }, 2000);

        // Poll for completion
        pollForCompletion(data.session_id);
    } catch (error) {
        addAssistantMessage(`❌ Failed to start conversion: ${error.message}`);
    }
}

// Check session status
async function checkSessionStatus(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/status`);

        if (!response.ok) {
            throw new Error(`Session not found or server error: ${response.status}`);
        }

        const data = await response.json();

        let statusMessage = `📊 **Session Status**

**Session ID:** \`${data.session_id}\`
**Workflow Stage:** ${data.workflow_stage}
**Progress:** ${data.progress_percentage}%
**Current Agent:** ${data.current_agent || 'None'}
**Status:** ${data.status_message}`;

        if (data.requires_clarification) {
            statusMessage += `\n\n⚠️ **Clarification Required:**\n${data.clarification_prompt}`;
        }

        addAssistantMessage(statusMessage);

        // If completed, fetch full context and show file links
        if (data.workflow_stage === 'completed') {
            await showCompletionFiles(sessionId);
        }
    } catch (error) {
        addAssistantMessage(`❌ Failed to get session status: ${error.message}`);
    }
}

// Refresh sessions list
async function refreshSessions() {
    // Note: The current API doesn't have a list sessions endpoint
    // This is a placeholder that could be implemented
    const sessionsList = document.getElementById('sessionsList');

    if (currentSessionId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${currentSessionId}/status`);
            if (response.ok) {
                const data = await response.json();
                activeSessions.set(data.session_id, data);
            }
        } catch (error) {
            console.error('Failed to fetch session:', error);
        }
    }

    if (activeSessions.size === 0) {
        sessionsList.innerHTML = '<p class="empty-state">No active sessions</p>';
    } else {
        sessionsList.innerHTML = Array.from(activeSessions.values())
            .map(session => `
                <div class="session-item" onclick="checkSessionStatus('${session.session_id}')">
                    <div class="session-id">${session.session_id.substring(0, 8)}...</div>
                    <div class="session-stage">${session.workflow_stage} (${session.progress_percentage}%)</div>
                </div>
            `).join('');
    }
}

// Show help message
function showHelpMessage() {
    const helpMessage = `🔧 **Available Commands**

**Conversion:**
• \`start conversion <path>\` - Start a new conversion
• \`convert <path>\` - Alias for start conversion

**Status:**
• \`status <session-id>\` - Check session status
• \`check status <session-id>\` - Check session status
• \`status\` - Check current session status

**System:**
• \`health\` - Check system health
• \`list sessions\` - Show all sessions
• \`help\` - Show this help message

**Examples:**
• \`start conversion ./tests/data/synthetic_openephys\`
• \`status abc123...\`
• \`list sessions\``;

    addAssistantMessage(helpMessage);
}

// UI Helper Functions

function addUserMessage(text) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';
    messageDiv.innerHTML = `
        <div class="message-avatar">👤</div>
        <div>
            <div class="message-content">${escapeHtml(text)}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addAssistantMessage(text, allowHtml = false) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';

    const content = allowHtml ? text : formatMarkdown(text);

    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div>
            <div class="message-content">${content}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addSystemMessage(text) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system';
    messageDiv.innerHTML = `
        <div class="message-avatar">ℹ️</div>
        <div>
            <div class="message-content">${escapeHtml(text)}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function showLoading() {
    const messagesContainer = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.id = 'loadingIndicator';
    loadingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="loading">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        </div>
    `;
    messagesContainer.appendChild(loadingDiv);
    scrollToBottom();
}

function hideLoading() {
    const loadingDiv = document.getElementById('loadingIndicator');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    // Simple markdown formatting
    let formatted = escapeHtml(text);

    // Bold
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

// Check for clarification requirement
async function checkForClarification(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/status`);
        if (!response.ok) return;

        const data = await response.json();

        if (data.requires_clarification) {
            showClarificationForm(sessionId, data.clarification_prompt);
        }
    } catch (error) {
        console.error('Failed to check clarification:', error);
    }
}

// Show clarification form
function showClarificationForm(sessionId, prompt) {
    const formHtml = `
<div class="clarification-form">
    <h3>⚠️ Missing Required Metadata</h3>
    <p>Please provide the following required information to continue with the conversion:</p>
    <form id="clarificationForm" onsubmit="submitClarification(event, '${sessionId}')">
        <div class="form-group">
            <label for="subject_id">Subject ID *</label>
            <input type="text" id="subject_id" name="subject_id" required placeholder="e.g., mouse_001, subject_A">
            <small>Identifier for the experimental subject</small>
        </div>
        <div class="form-group">
            <label for="species">Species *</label>
            <input type="text" id="species" name="species" required placeholder="e.g., Mus musculus, Homo sapiens">
            <small>Scientific species name</small>
        </div>
        <div class="form-group">
            <label for="sex">Sex *</label>
            <select id="sex" name="sex" required>
                <option value="">Select...</option>
                <option value="M">Male (M)</option>
                <option value="F">Female (F)</option>
                <option value="U">Unknown (U)</option>
                <option value="O">Other (O)</option>
            </select>
            <small>Sex of the subject</small>
        </div>
        <div class="form-group">
            <label for="experimenter">Experimenter *</label>
            <input type="text" id="experimenter" name="experimenter" required placeholder="e.g., Smith, John">
            <small>Name(s) of the experimenter(s)</small>
        </div>
        <button type="submit" class="btn-primary">Submit & Continue Conversion</button>
    </form>
</div>`;

    addAssistantMessage(formHtml, true); // Allow HTML for form rendering
}

// Submit clarification
async function submitClarification(event, sessionId) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const metadata = {};

    for (const [key, value] of formData.entries()) {
        metadata[key] = value;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/clarify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ updated_metadata: metadata }),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        addAssistantMessage('✅ Metadata submitted! Conversion will now continue...');
        form.remove();

        // Check status after a delay
        setTimeout(async () => {
            await checkSessionStatus(sessionId);
        }, 3000);

    } catch (error) {
        addAssistantMessage(`❌ Failed to submit metadata: ${error.message}`);
    }
}

// Poll for completion
async function pollForCompletion(sessionId, maxAttempts = 60) {
    let attempts = 0;
    const pollInterval = setInterval(async () => {
        attempts++;

        if (attempts > maxAttempts) {
            clearInterval(pollInterval);
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/status`);
            if (!response.ok) {
                clearInterval(pollInterval);
                return;
            }

            const data = await response.json();

            if (data.workflow_stage === 'completed') {
                clearInterval(pollInterval);
                addAssistantMessage('🎉 **Conversion completed!** Fetching your files...');
                await showCompletionFiles(sessionId);
            } else if (data.workflow_stage === 'failed') {
                clearInterval(pollInterval);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 3000); // Poll every 3 seconds
}

// Show completion files with download links
async function showCompletionFiles(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/internal/sessions/${sessionId}/context`);
        if (!response.ok) return;

        const context = await response.json();

        // Extract file paths
        const nwbFile = context.conversion_results?.nwb_file_path;
        const reportFile = context.validation_results?.validation_report_path;
        const overallStatus = context.validation_results?.overall_status;

        if (!nwbFile && !reportFile) return;

        // Create file links HTML
        let filesHtml = `
<div class="completion-files">
    <h3>✅ Conversion Completed Successfully!</h3>
    <p>Your files are ready for download:</p>
    <div class="file-links">`;

        if (nwbFile) {
            const fileName = nwbFile.split(/[/\\]/).pop();
            const fileUrl = `${API_BASE_URL}/api/v1/downloads/nwb/${fileName}`;
            filesHtml += `
        <div class="file-item">
            <span class="file-icon">📄</span>
            <div class="file-info">
                <strong>NWB File</strong>
                <small>${fileName}</small>
            </div>
            <a href="${fileUrl}" download="${fileName}" class="download-btn">Download NWB</a>
        </div>`;
        }

        if (reportFile) {
            const fileName = reportFile.split(/[/\\]/).pop();
            const fileUrl = `${API_BASE_URL}/api/v1/downloads/report/${fileName}`;
            filesHtml += `
        <div class="file-item">
            <span class="file-icon">📊</span>
            <div class="file-info">
                <strong>Validation Report</strong>
                <small>${fileName}</small>
                ${overallStatus ? `<span class="status-badge status-${overallStatus}">${overallStatus}</span>` : ''}
            </div>
            <a href="${fileUrl}" download="${fileName}" class="download-btn">Download Report</a>
        </div>`;
        }

        filesHtml += `
    </div>
</div>`;

        addAssistantMessage(filesHtml, true);
    } catch (error) {
        console.error('Failed to fetch completion files:', error);
    }
}
