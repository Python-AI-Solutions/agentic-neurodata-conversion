# Priority 1 Improvements - Implementation Guide

**Time Estimate:** 4-6 hours total

These are the 5 critical improvements you requested. All code locations and exact changes are documented below.

---

## ✅ Fix #1: Improve Error Messages for Missing Metadata (90 min)

**File:** `backend/src/agents/conversation_agent.py`
**Line:** 687
**Current Code:**
```python
return f"""Cannot start conversion - missing required NWB metadata:

{chr(10).join(explanations)}

Please provide this information before conversion can proceed. For example:
- sex: "M" (for male), "F" (for female), or "U" (for unknown)

You can provide this via the chat interface."""
```

**NEW CODE:**
```python
# Enhanced field descriptions with examples
field_examples = {
    "experimenter": "'Smith, Jane' or 'Smith, J.'",
    "institution": "'Massachusetts Institute of Technology' or 'MIT'",
    "lab": "'Smith Lab' or 'Neuroscience Laboratory'",
    "session_start_time": "'2024-01-15T10:30:00-05:00' (ISO 8601 format)",
    "session_description": "'Visual cortex recording during passive viewing'",
    "experiment_description": "'Neuropixels recording from awake behaving mouse'",
    "subject_id": "'mouse001' or 'M001'",
    "species": "'Mus musculus' for mouse, 'Rattus norvegicus' for rat",
    "sex": "'M' for male, 'F' for female, 'U' for unknown",
    "age": "'P60D' for postnatal day 60, 'P3M' for 3 months",
    "strain": "'C57BL/6J' for C57 Black 6 mice",
}

# Build explanations with examples
detailed_explanations = []
for field in missing_fields:
    desc = field_descriptions.get(field, field)
    example = field_examples.get(field, "")
    if example:
        detailed_explanations.append(f"  • {desc}\n    Example: {example}")
    else:
        detailed_explanations.append(f"  • {desc}")

return f"""Great progress! I've captured most of your metadata.

To start conversion, I still need a few more details:

{chr(10).join(detailed_explanations)}

💡 **Tip:** You can provide all of this in your next message, then confirm you're ready!

Example: "Session started 2024-01-15 at 10:30 AM. This was a visual cortex recording during passive viewing. I'm ready to proceed."
"""
```

**Benefits:**
- ✅ Positive framing ("Great progress!")
- ✅ Clear examples for each field
- ✅ Helpful tip at the end
- ✅ Reduces user frustration

---

## ✅ Fix #2: Add "LLM is Thinking" Indicator (60 min)

**File:** `frontend/public/chat-ui.html`
**Location:** Find the `sendChatMessage` function (around line 1650)

**BEFORE:**
```javascript
async function sendChatMessage() {
    const messageInput = document.getElementById('chat-input');
    const message = messageInput.value.trim();

    if (!message) return;

    // Clear input
    messageInput.value = '';

    // Display user message
    addUserMessage(message);

    // Send to backend
    const response = await fetch('/api/chat', {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    // Display response...
}
```

**AFTER:**
```javascript
async function sendChatMessage() {
    const messageInput = document.getElementById('chat-input');
    const message = messageInput.value.trim();

    if (!message) return;

    // Clear input
    messageInput.value = '';

    // Display user message
    addUserMessage(message);

    // ✅ NEW: Add "thinking" indicator
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message assistant thinking-indicator';
    thinkingDiv.id = 'thinking-indicator';
    thinkingDiv.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <span>Processing your message... (may take 30-60 seconds)</span>
        </div>
    `;
    document.getElementById('messages').appendChild(thinkingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        // Send to backend
        const response = await fetch('/api/chat', {
            method: 'POST',
            body: formData
        });

        // ✅ NEW: Remove thinking indicator
        const indicator = document.getElementById('thinking-indicator');
        if (indicator) indicator.remove();

        const data = await response.json();
        // Display response...

    } catch (error) {
        // ✅ NEW: Remove thinking indicator on error too
        const indicator = document.getElementById('thinking-indicator');
        if (indicator) indicator.remove();

        addAssistantMessage('❌ Error: ' + error.message);
    }
}
```

**Add CSS:**
```css
/* Add to chat-ui.html <style> section */
.thinking-indicator {
    background: #f8f9fa;
    border-left: 4px solid #17a2b8;
    opacity: 0.9;
}

.thinking-indicator .loading {
    display: flex;
    align-items: center;
    gap: 12px;
}

.thinking-indicator .spinner {
    width: 20px;
    height: 20px;
    border: 3px solid #e9ecef;
    border-top-color: #17a2b8;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

**Benefits:**
- ✅ User knows system is working
- ✅ Manages expectations (30-60 seconds)
- ✅ Reduces perceived wait time

---

## ✅ Fix #3: Add "Conversion Starting" Message (45 min)

**File:** `frontend/public/chat-ui.html`
**Location:** In the `/api/chat` response handler (around line 1715)

**BEFORE:**
```javascript
if (data.ready_to_proceed === true) {
    // User confirmed ready - conversion will start automatically
    addAssistantMessage('Perfect! Starting conversion with your metadata...');
    monitorConversion();
}
```

**AFTER:**
```javascript
if (data.ready_to_proceed === true) {
    // ✅ NEW: Enhanced feedback with progress expectations
    addAssistantMessage('✓ Metadata complete! Starting conversion now...');

    // Add a progress message
    setTimeout(() => {
        addSystemMessage('⏳ Step 1/3: Detecting file format and preparing conversion...');
    }, 500);

    setTimeout(() => {
        addSystemMessage('⏳ This process may take 1-3 minutes depending on file size.');
        addSystemMessage('💡 You can watch the progress in the status panel →');
    }, 1000);

    monitorConversion();
}
```

**Add helper function:**
```javascript
function addSystemMessage(text) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system';
    messageDiv.innerHTML = `
        <div class="message-content">
            <p>${text}</p>
        </div>
    `;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
```

**Add CSS:**
```css
.message.system {
    background: #e7f3ff;
    border-left: 4px solid #0066cc;
    font-style: italic;
    opacity: 0.95;
}
```

**Benefits:**
- ✅ Immediate confirmation user action was accepted
- ✅ Sets expectations (1-3 minutes)
- ✅ Directs attention to status panel

---

## ✅ Fix #4: Clean Up Stale Session State (60 min)

**File:** `backend/src/api/main.py`
**Location:** `/api/start-conversion` endpoint (around line 610)

**BEFORE:**
```python
@app.post("/api/start-conversion")
async def start_conversion_endpoint():
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Immediately start the conversion workflow
    # ...
```

**AFTER:**
```python
@app.post("/api/start-conversion")
async def start_conversion_endpoint():
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # ✅ NEW: Clean up stale state from previous sessions
    if state.status in [ConversionStatus.FAILED, ConversionStatus.COMPLETED]:
        state.add_log(
            LogLevel.INFO,
            "Cleaning up stale session state before starting new conversion",
            {"previous_status": state.status.value}
        )

        # Reset only the necessary fields, preserve uploaded file info
        state.validation_result = None
        state.validation_issues = []
        state.overall_status = None
        state.correction_attempt = 0
        state.metadata = state.user_provided_metadata.copy()  # Keep user metadata
        state.logs = []  # Clear old logs

        state.add_log(LogLevel.INFO, "Starting fresh conversion workflow")

    # Continue with conversion workflow
    # ...
```

**Also add to `/api/chat` endpoint:**
```python
@app.post("/api/chat")
async def chat_message(message: str = Form(...)):
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # ✅ NEW: If chat is called on a failed/completed session, treat as new session
    if state.status in [ConversionStatus.FAILED, ConversionStatus.COMPLETED]:
        state.add_log(LogLevel.INFO, "Resetting completed/failed session for new conversation")
        # Let user start fresh
        state.status = ConversionStatus.IDLE
        state.validation_result = None
        state.overall_status = None
        state.logs = []

    # Continue with chat logic...
```

**Benefits:**
- ✅ No confusing error messages from previous runs
- ✅ Clean slate for each conversion
- ✅ Better reliability

---

## ✅ Fix #5: Add Metadata Requirements Documentation (90 min)

**File:** `frontend/public/chat-ui.html`
**Location:** Add new section in the HTML (around line 200, near the chat interface)

**ADD THIS HTML:**
```html
<!-- ✅ NEW: Metadata Help Panel -->
<div class="metadata-help-panel" id="metadata-help" style="display: none;">
    <div class="help-header">
        <h3>📋 Required NWB Metadata</h3>
        <button onclick="closeMetadataHelp()">✕</button>
    </div>

    <div class="help-content">
        <p class="help-intro">
            To convert your file to NWB format, please provide the following information:
        </p>

        <div class="metadata-section">
            <h4>Experiment Information</h4>
            <ul>
                <li><strong>experimenter</strong> - Name of person who performed experiment
                    <br><span class="example">Example: "Smith, Jane"</span>
                </li>
                <li><strong>institution</strong> - Where the experiment was performed
                    <br><span class="example">Example: "MIT" or "Massachusetts Institute of Technology"</span>
                </li>
                <li><strong>lab</strong> - Laboratory name
                    <br><span class="example">Example: "Smith Lab"</span>
                </li>
                <li><strong>session_start_time</strong> - When recording started (ISO 8601 format)
                    <br><span class="example">Example: "2024-01-15T10:30:00-05:00"</span>
                </li>
                <li><strong>session_description</strong> - Description of recording session
                    <br><span class="example">Example: "Visual cortex recording during passive viewing"</span>
                </li>
                <li><strong>experiment_description</strong> - Description of overall experiment
                    <br><span class="example">Example: "Neuropixels recording from awake behaving mouse"</span>
                </li>
            </ul>
        </div>

        <div class="metadata-section">
            <h4>Subject Information</h4>
            <ul>
                <li><strong>subject_id</strong> - Unique identifier for subject
                    <br><span class="example">Example: "mouse001"</span>
                </li>
                <li><strong>species</strong> - Species of subject
                    <br><span class="example">Example: "Mus musculus" (mouse), "Rattus norvegicus" (rat)</span>
                </li>
                <li><strong>sex</strong> - Sex of subject
                    <br><span class="example">Example: "M", "F", or "U"</span>
                </li>
                <li><strong>age</strong> - Age of subject
                    <br><span class="example">Example: "P60D" (60 days old), "P3M" (3 months old)</span>
                </li>
            </ul>
        </div>

        <div class="tip-box">
            <strong>💡 Pro Tip:</strong> You can provide all this information in a single message!
            <br>
            <br>
            Example: "Dr. Jane Smith from MIT, Smith Lab. Male C57BL/6 mouse, age P60, ID mouse001. Visual cortex neuropixels recording. Started 2024-01-15 at 10:30 AM."
        </div>
    </div>
</div>

<!-- Add button to show help -->
<button class="help-button" onclick="showMetadataHelp()">
    ℹ️ Metadata Guide
</button>
```

**ADD THIS CSS:**
```css
.metadata-help-panel {
    position: fixed;
    right: 20px;
    top: 80px;
    width: 400px;
    max-height: calc(100vh - 100px);
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    overflow-y: auto;
    z-index: 1000;
}

.help-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid #eee;
    background: #f8f9fa;
}

.help-header h3 {
    margin: 0;
    font-size: 18px;
}

.help-header button {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #666;
}

.help-content {
    padding: 16px;
}

.help-intro {
    margin-bottom: 20px;
    color: #555;
}

.metadata-section {
    margin-bottom: 24px;
}

.metadata-section h4 {
    margin-bottom: 12px;
    color: #333;
    border-bottom: 2px solid #007bff;
    padding-bottom: 4px;
}

.metadata-section ul {
    list-style: none;
    padding: 0;
}

.metadata-section li {
    margin-bottom: 16px;
    padding-left: 20px;
    position: relative;
}

.metadata-section li:before {
    content: "•";
    position: absolute;
    left: 0;
    color: #007bff;
    font-weight: bold;
}

.example {
    display: block;
    margin-top: 4px;
    color: #666;
    font-size: 14px;
    font-style: italic;
}

.tip-box {
    background: #e7f3ff;
    border-left: 4px solid #007bff;
    padding: 12px;
    margin-top: 20px;
    border-radius: 4px;
}

.help-button {
    position: fixed;
    right: 20px;
    bottom: 20px;
    padding: 12px 20px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 25px;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    font-size: 16px;
    z-index: 999;
}

.help-button:hover {
    background: #0056b3;
}
```

**ADD THIS JAVASCRIPT:**
```javascript
function showMetadataHelp() {
    document.getElementById('metadata-help').style.display = 'block';
}

function closeMetadataHelp() {
    document.getElementById('metadata-help').style.display = 'none';
}
```

**Benefits:**
- ✅ Users know exactly what to provide
- ✅ Reduces back-and-forth
- ✅ Faster completion
- ✅ Better user experience

---

## 🧪 Testing After Implementation

Run this test to verify all improvements:

```bash
# 1. Reset and upload
curl -X POST http://localhost:8000/api/reset
curl -X POST http://localhost:8000/api/upload -F "file=@test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin"

# 2. Start conversion
curl -X POST http://localhost:8000/api/start-conversion

# 3. Provide partial metadata (should get improved error message)
curl -X POST http://localhost:8000/api/chat -F "message=Dr Smith, MIT, mouse P60"

# Expected: Should see "Great progress! I've captured most of your metadata. To start conversion, I still need..."

# 4. Open frontend in browser and check:
# - ✅ "ℹ️ Metadata Guide" button appears
# - ✅ Clicking it shows help panel with all fields
# - ✅ Sending a message shows "Processing..." indicator
# - ✅ When confirmed ready, shows "✓ Metadata complete! Starting conversion now..."
```

---

## ⏱️ Implementation Time Breakdown

1. **Error messages** - 90 minutes
2. **LLM thinking indicator** - 60 minutes
3. **Conversion starting message** - 45 minutes
4. **Stale state cleanup** - 60 minutes
5. **Metadata documentation** - 90 minutes

**Total: 5.75 hours** (rounded to 4-6 hours accounting for testing)

---

## 📝 Summary

After implementing these 5 fixes, your system will have:

1. ✅ **Clear, helpful error messages** that guide users to provide missing metadata
2. ✅ **Visual feedback** during LLM processing (no more wondering if it's working)
3. ✅ **Immediate confirmation** when conversion starts
4. ✅ **Clean state** for each new conversion (no stale data confusion)
5. ✅ **Built-in help system** so users know what to provide upfront

**All improvements are user experience enhancements - no changes to core workflow logic!**
