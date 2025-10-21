# Frontend Fix Instructions
## Implementing Conversational Metadata Workflow

**Date:** 2025-10-20
**Objective:** Fix frontend to match backend's three-agent conversational workflow
**Estimated Time:** 2-3 hours
**Files to Modify:** `frontend/public/chat-ui.html`

---

## Executive Summary

The frontend currently uploads files with hardcoded metadata, bypassing the entire conversational metadata collection workflow. This fix removes hardcoded metadata and implements proper conversational flow.

---

## Changes Required

### Change 1: Modify `startConversion()` Function (Lines 1195-1268)

**Current Problem:**
```javascript
// Lines 1221-1223 - HARDCODED METADATA
formData.append('metadata', JSON.stringify({
    session_description: 'Conversion via chat interface'  // ❌ WRONG
}));
```

**Fix - Replace entire `startConversion()` function:**

```javascript
// Conversion workflow
async function startConversion() {
    if (!currentFiles || currentFiles.length === 0) {
        addAssistantMessage('Please select at least one file first.');
        return;
    }

    // UX Fix #3: Disable previous buttons (Start Conversion, Add Metadata)
    disablePreviousButtons();
    updateWorkflowState({ stage: 'metadata_collection', canStartConversion: false, canAddMetadata: false });

    conversionInProgress = true;
    startLogsAutoRefresh(); // Start auto-refreshing logs

    // ✅ FIX: Upload file WITHOUT metadata first
    const formData = new FormData();

    // Append all files - backend will determine which to use
    currentFiles.forEach((file, index) => {
        if (index === 0) {
            formData.append('file', file);
        } else {
            formData.append('additional_files', file);
        }
    });

    // ✅ DO NOT append metadata - let backend request it via conversation

    try {
        addLoadingMessage();

        // Step 1: Upload file (without metadata)
        const uploadResponse = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            removeLoadingMessage();
            addAssistantMessage(`❌ Upload failed: ${error.detail || 'Unknown error'}`);
            conversionInProgress = false;
            return;
        }

        const uploadData = await uploadResponse.json();
        removeLoadingMessage();

        // Don't show upload message - backend will request metadata next
        console.log('Upload successful:', uploadData);

        // Step 2: Start conversion workflow
        addLoadingMessage();
        const startResponse = await fetch(`${API_BASE}/api/start-conversion`, {
            method: 'POST'
        });

        removeLoadingMessage();

        if (startResponse.ok) {
            const startData = await startResponse.json();

            // ✅ FIX: Check if backend is requesting metadata
            const statusResponse = await fetch(`${API_BASE}/api/status`);
            const statusData = await statusResponse.json();

            if (statusData.conversation_type === 'required_metadata' ||
                statusData.status === 'awaiting_user_input') {
                // Backend is requesting metadata - guide user to provide it
                showMetadataCollectionPrompt();
            } else {
                // Backend proceeding without metadata (unlikely but handle it)
                addAssistantMessage(startData.message || '🚀 Conversion started!');
            }

            monitorConversion();
        } else {
            const error = await startResponse.json();
            addAssistantMessage(`❌ Failed to start conversion: ${error.detail || 'Unknown error'}`);
            conversionInProgress = false;
        }
    } catch (error) {
        removeLoadingMessage();
        addAssistantMessage(`❌ Error: ${error.message}`);
        conversionInProgress = false;
    }
}
```

---

### Change 2: Add New Helper Function `showMetadataCollectionPrompt()` (After line 1268)

**Add this NEW function:**

```javascript
// NEW FUNCTION: Guide user through metadata collection
function showMetadataCollectionPrompt() {
    addAssistantMessage(
        "📋 Before converting, I need some information about your experiment. " +
        "You can provide details naturally, like:\n\n" +
        "\"Dr Jane Smith from MIT, male C57BL/6 mouse age P60 ID mouse001, visual cortex recording\"\n\n" +
        "Or just tell me piece by piece - I'll ask for what I need!"
    );

    // Highlight chat input to guide user
    const textInput = document.getElementById('textInput');
    textInput.focus();
    textInput.placeholder = "Type experiment details (experimenter, institution, subject, etc.)...";
    textInput.style.borderColor = '#667eea';
    textInput.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)';

    // Reset border after user starts typing
    textInput.addEventListener('input', function resetBorder() {
        textInput.style.borderColor = '';
        textInput.style.boxShadow = '';
        textInput.removeEventListener('input', resetBorder);
    }, { once: true });

    // Update workflow state
    workflowState.stage = 'collecting_metadata';
}
```

---

### Change 3: Enhance `handleUserInputRequest()` (Lines 1367-1406)

**Current code is partially correct but needs enhancement:**

**Replace function with:**

```javascript
async function handleUserInputRequest() {
    // Get the current status which includes the message
    const statusResponse = await fetch(`${API_BASE}/api/status`);
    const statusData = await statusResponse.json();

    // ✅ FIX: Handle metadata collection more explicitly
    if (statusData.conversation_type === 'required_metadata') {
        // Backend is requesting metadata via conversation
        if (statusData.message) {
            const messageHash = statusData.message.split(' ').slice(0, 20).join(' ');
            const statusChanged = lastDisplayedStatus !== statusData.status;

            if (lastDisplayedMessage !== messageHash || statusChanged) {
                removeLoadingMessage();

                // Show backend's metadata request message
                addAssistantMessage(statusData.message);

                // Highlight chat input
                const textInput = document.getElementById('textInput');
                textInput.focus();
                textInput.placeholder = "Provide metadata details...";

                // Update tracking variables
                lastDisplayedMessage = messageHash;
                lastDisplayedStatus = statusData.status;
            }
        } else {
            // No message yet - show generic prompt
            showMetadataCollectionPrompt();
        }

        // Enable conversational input
        enableConversationalInput();
    } else {
        // Legacy handling for other awaiting_user_input states
        if (statusData.message) {
            const messageHash = statusData.message ?
                statusData.message.split(' ').slice(0, 20).join(' ') :
                `${statusData.status}_${statusData.conversation_type}`;
            const statusChanged = lastDisplayedStatus !== statusData.status;

            if (lastDisplayedMessage !== messageHash || statusChanged) {
                removeLoadingMessage();
                addAssistantMessage(statusData.message);
                lastDisplayedMessage = messageHash;
                lastDisplayedStatus = statusData.status;
            }

            enableConversationalInput();
        }
    }
}
```

---

### Change 4: Enhance `sendConversationalMessage()` (Lines 1645-1687)

**Current code is good but needs metadata confirmation handling:**

**Replace function with:**

```javascript
async function sendConversationalMessage(message) {
    addLoadingMessage();

    try {
        const formData = new FormData();
        formData.append('message', message);

        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();

            // Remove loading message
            removeLoadingMessage();

            // ✅ FIX: Show extracted metadata to user
            if (data.extracted_metadata && Object.keys(data.extracted_metadata).length > 0) {
                let metadataHtml = '<div style="background: #f0f7ff; padding: 12px; border-radius: 8px; margin-top: 8px;">';
                metadataHtml += '<strong>✓ Extracted metadata:</strong><br>';
                for (const [key, value] of Object.entries(data.extracted_metadata)) {
                    const displayValue = Array.isArray(value) ? value.join(', ') : value;
                    metadataHtml += `<span style="color: #666; font-size: 0.9em;">• ${key}: ${displayValue}</span><br>`;
                }
                metadataHtml += '</div>';

                // Show metadata in last message
                const messagesContainer = document.getElementById('messages');
                const lastUserMessage = messagesContainer.lastElementChild;
                if (lastUserMessage && lastUserMessage.classList.contains('user')) {
                    const bubble = lastUserMessage.querySelector('.message-bubble');
                    if (bubble) {
                        bubble.innerHTML += metadataHtml;
                    }
                }
            }

            // Display LLM's response
            if (data.message) {
                addAssistantMessage(data.message);
            }

            // ✅ FIX: Check if conversation is continuing or ready to proceed
            if (data.ready_to_proceed === true) {
                // User confirmed ready - show confirmation
                addAssistantMessage(
                    '✅ Great! I have all the information needed. Starting conversion now...',
                    []
                );

                // Conversion will start automatically via backend
                // Continue monitoring
                monitorConversion();
            } else if (data.needs_more_info) {
                // Continue conversation - user can respond again
                enableConversationalInput();

                // Keep chat input highlighted
                const textInput = document.getElementById('textInput');
                textInput.focus();
            } else {
                // Unexpected state - monitor anyway
                monitorConversion();
            }
        } else {
            removeLoadingMessage();
            addAssistantMessage('❌ Sorry, I had trouble processing your response. Could you try again?');
        }
    } catch (error) {
        removeLoadingMessage();
        addAssistantMessage(`❌ Error: ${error.message}`);
    }
}
```

---

### Change 5: Update File Selection Handler (Lines 932-954)

**Current code shows two buttons. Keep the "Add Metadata First" option but change behavior:**

**Replace with:**

```javascript
// File handling
document.getElementById('fileInput').addEventListener('change', async (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        currentFiles = files;

        // Display all selected files
        const fileNames = files.map(f => f.name).join(', ');
        const fileCount = files.length;
        const message = fileCount === 1
            ? `📎 Selected file: ${fileNames}`
            : `📎 Selected ${fileCount} files: ${fileNames}`;

        addUserMessage(message);

        // UX Fix #3: Update workflow state to uploaded
        updateWorkflowState({ stage: 'uploaded', canStartConversion: true, canAddMetadata: true });

        // ✅ FIX: New message explaining conversational workflow
        addAssistantMessage(
            'Perfect! I\'ll guide you through adding metadata for better NWB quality.\n\n' +
            'When you click "Start Conversion", I\'ll ask you some questions about your experiment. ' +
            'Or you can provide details upfront if you prefer!',
            [
                { text: '🚀 Start Conversion (I\'ll guide you)', onClick: () => startConversion(), variant: 'primary' },
                { text: '📝 Tell me about the experiment now', onClick: () => showMetadataCollectionPrompt(), variant: 'secondary' }
            ]
        );
    }
});
```

---

### Change 6: Update `requestMetadata()` Function (Lines 1556-1559)

**Replace with:**

```javascript
function requestMetadata() {
    addUserMessage('📝 I want to provide metadata details first');
    showMetadataCollectionPrompt();
}
```

---

## Testing Instructions

### Step 1: Apply Changes
1. Open `frontend/public/chat-ui.html`
2. Apply all 6 changes listed above
3. Save the file
4. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+F5)

### Step 2: Manual Test - Happy Path
1. Open browser to `http://localhost:8000/frontend/public/chat-ui.html`
2. Select test file: `test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin`
3. Click "🚀 Start Conversion (I'll guide you)"
4. Should see: Message requesting metadata
5. Type: "Dr Jane Smith from MIT, male mouse age P60 ID mouse001, visual cortex recording"
6. Should see: Extracted metadata displayed below your message
7. Should see: LLM asking if ready or needs more info
8. Type: "I'm ready to proceed" or "Start conversion"
9. Should see: "Starting conversion now..."
10. Should see: Status changes from `awaiting_user_input` → `converting` → `validating` → `completed`

### Step 3: Manual Test - Provide Metadata Upfront
1. Reset: Click "New Conversion"
2. Select file
3. Click "📝 Tell me about the experiment now"
4. Type metadata before conversion starts
5. When ready, type "Start conversion"
6. Should proceed directly to conversion

### Step 4: API Test to Verify Backend Unchanged
```bash
# Test that backend still works with direct API calls
curl -X POST http://localhost:8000/api/reset -s

# Upload without metadata
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin" -s

# Start conversion
curl -X POST http://localhost:8000/api/start-conversion -s

# Check status - should request metadata
curl -s http://localhost:8000/api/status | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'conversation_type: {d.get(\"conversation_type\")}')"
# Expected: conversation_type: required_metadata

# Provide metadata
curl -X POST http://localhost:8000/api/chat \
  -F "message=Dr Smith, MIT, mouse P60" -s

# Confirm ready
curl -X POST http://localhost:8000/api/chat \
  -F "message=I'm ready" -s

# Check status - should be converting
curl -s http://localhost:8000/api/status | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'status: {d.get(\"status\")}')"
# Expected: status: converting or validating
```

---

## What These Changes Fix

### Before (Broken):
```
User uploads file
  ↓
Clicks "Start Conversion"
  ↓
Frontend uploads WITH hardcoded metadata
  ↓
Backend skips metadata collection
  ↓
Poor quality conversion OR system stuck
```

### After (Fixed):
```
User uploads file
  ↓
Clicks "Start Conversion"
  ↓
Frontend uploads WITHOUT metadata
  ↓
Backend requests metadata
  ↓
Frontend shows prompt
  ↓
User provides metadata via chat
  ↓
Backend extracts metadata (shown to user)
  ↓
User confirms "ready"
  ↓
Backend starts conversion with proper metadata
  ↓
Three-agent workflow: Agent 1 → Agent 2 → Agent 3
  ↓
Quality NWB file
```

---

## Expected User Experience After Fix

### Scenario 1: Guided Metadata Collection
1. **User:** Uploads `recording.bin`
2. **UI:** "Perfect! I'll guide you through adding metadata. Click 'Start Conversion'"
3. **User:** Clicks "Start Conversion"
4. **UI:** "Before converting, I need some information. Who's the experimenter?"
5. **User:** Types: "Dr Jane Smith from MIT"
6. **UI:** "✓ Extracted: experimenter: Smith, Jane; institution: MIT"
7. **UI:** "Got it! What about the subject? (species, age, ID)"
8. **User:** "Male mouse, age P60, ID mouse001"
9. **UI:** "✓ Extracted: species: Mus musculus, age: P60D, subject_id: mouse001"
10. **UI:** "Perfect! Ready to convert?"
11. **User:** "Yes"
12. **UI:** "✅ Starting conversion with complete metadata..."
13. **UI:** Shows conversion progress → validation → download

### Scenario 2: Provide Metadata Upfront
1. **User:** Uploads file
2. **UI:** Shows two buttons
3. **User:** Clicks "Tell me about the experiment now"
4. **UI:** "Great! Provide details..."
5. **User:** Types all metadata at once
6. **UI:** Shows extracted metadata
7. **User:** "Start conversion"
8. **UI:** Proceeds to conversion

---

## Rollback Instructions

If something goes wrong, rollback is simple:

1. Keep backup of original `chat-ui.html`:
```bash
cp frontend/public/chat-ui.html frontend/public/chat-ui.html.backup
```

2. To rollback:
```bash
cp frontend/public/chat-ui.html.backup frontend/public/chat-ui.html
```

---

## Additional Enhancements (Optional - Phase 2)

After basic fix is working, consider:

###1. Visual Workflow Progress Indicator
```html
<!-- Add to chat header -->
<div class="workflow-progress">
    <div class="step" data-step="upload">Upload</div>
    <div class="step active" data-step="metadata">Metadata</div>
    <div class="step" data-step="convert">Convert</div>
    <div class="step" data-step="validate">Validate</div>
    <div class="step" data-step="download">Download</div>
</div>
```

### 2. Metadata Summary Before Conversion
```javascript
function showMetadataSummary(metadata) {
    let html = '<div class="metadata-summary">';
    html += '<h4>📋 Collected Metadata Summary:</h4>';
    for (const [key, value] of Object.entries(metadata)) {
        html += `<div>${key}: ${value}</div>`;
    }
    html += '</div>';

    addAssistantMessage(html, [
        { text: '✓ Looks good, convert now', onClick: confirmConversion, variant: 'primary' },
        { text: '✏️ Edit metadata', onClick: editMetadata, variant: 'secondary' }
    ]);
}
```

### 3. Metadata Field Validation
```javascript
function validateMetadata(metadata) {
    const required = ['experimenter', 'institution', 'subject_id'];
    const missing = required.filter(field => !metadata[field]);

    if (missing.length > 0) {
        addAssistantMessage(
            `⚠️ Still missing: ${missing.join(', ')}. Should I proceed anyway or would you like to add these?`,
            [
                { text: 'Add missing fields', onClick: () => requestMissingFields(missing) },
                { text: 'Proceed anyway', onClick: confirmConversion }
            ]
        );
        return false;
    }
    return true;
}
```

---

## Summary

**Changes:** 6 function modifications in `chat-ui.html`
**Lines Modified:** ~300 lines total
**Backend Changes:** **ZERO** - Backend is perfect as-is
**Testing Time:** 15-20 minutes
**Implementation Time:** 2-3 hours
**Impact:** Enables full three-agent conversational workflow for all users

**Priority:** **P0 - Critical** - This is the missing piece preventing users from accessing the intelligent workflow you built.
