# Chat-Based UI - Claude.ai Style

A modern, conversational interface for the Agentic Neurodata Conversion system, inspired by Claude.ai.

## Features

### 🎨 Modern Design
- Clean, minimal interface with smooth animations
- Sidebar with connection status
- Message bubbles with avatar icons
- Status badges with color coding
- Responsive layout

### 💬 Chat-Based Workflow
- Natural conversation flow
- File upload via attachment button or drag-and-drop
- Interactive action buttons within messages
- Real-time status updates via WebSocket
- Loading indicators for async operations

### 🔄 Complete Conversion Flow
1. **File Selection**: Upload via button or chat
2. **Metadata (Optional)**: Add details before conversion
3. **Automatic Conversion**: Progress tracked in real-time
4. **Validation**: Issues displayed with context
5. **Retry Approval**: Auto-fixable vs user-input-required breakdown
6. **User Input Modal**: Dynamic form for missing metadata
7. **Download**: One-click NWB file download

## Usage

### Access the Chat UI

Open in your browser:
```
file:///Users/adityapatane/agentic-neurodata-conversion-14/frontend/public/chat-ui.html
```

Or serve it:
```bash
cd frontend/public
python -m http.server 3000
# Then visit: http://localhost:3000/chat-ui.html
```

### Quick Start

1. **Upload File**: Click the 📎 button or drag a file into the chat
2. **Confirm**: Choose "Start Conversion" or "Add Metadata First"
3. **Monitor**: Watch real-time status updates in the chat
4. **Handle Issues**: If validation fails, choose to retry or decline
5. **Download**: Click "Download NWB File" when complete

## Interface Components

### Sidebar
- **Header**: System name and description
- **New Conversation**: Reset and start fresh
- **Connection Status**: Real-time WebSocket connection indicator
  - 🟢 Green = Connected
  - 🔴 Red = Disconnected

### Chat Area
- **Header**: Shows current conversation status
- **Messages**: Scrollable conversation history
- **Input Bar**: Text input, file attachment, send button

### Status Badge Colors
- 🔵 Blue: Detecting format
- 🟡 Yellow: Converting
- 🟣 Purple: Validating
- 🟢 Green: Completed
- 🔴 Red: Failed
- 🟠 Orange: Awaiting retry approval
- 🩷 Pink: Awaiting user input

### Message Types

**Assistant Messages** (Left side, gray bubble):
- Welcome message
- Status updates
- Issue breakdowns
- Action prompts

**User Messages** (Right side, purple gradient bubble):
- File selections
- Action confirmations
- Text input

**Action Buttons**:
- Primary (Purple): Main actions like "Start Conversion"
- Success (Green): Download actions
- Secondary (Gray): Cancel or alternative actions
- Danger (Red): Decline or stop actions

## Comparison: Old UI vs Chat UI

### Old UI (index.html)
- Status-card based interface
- Manual refresh/polling
- Form-based input
- Multiple disconnected screens

### Chat UI (chat-ui.html)
- Conversational interface
- Real-time WebSocket updates
- Interactive message-based input
- Unified single-page experience

## Technical Details

### WebSocket Integration
```javascript
// Automatic connection with reconnection
connectWebSocket()
- Auto-reconnect with exponential backoff
- Connection status indicator
- Real-time event handling
```

### Message Flow
```javascript
addUserMessage(text)        // User actions
addAssistantMessage(text, actions)  // System responses
addLoadingMessage()         // Processing indicator
```

### Action Buttons
```javascript
{
  text: '🚀 Start Conversion',
  onClick: () => startConversion(),
  variant: 'primary'  // primary, secondary, success, danger
}
```

### Modal Forms
Dynamic form generation from backend field specifications:
```javascript
showUserInputModal(fields)
// fields = [{ field_name, label, type, required, help_text }]
```

## Customization

### Colors
Edit CSS variables in the `<style>` section:
```css
/* Primary brand color */
background: #667eea;  /* Purple gradient */

/* Status colors */
.status-completed { background: #d1fae5; }
.status-failed { background: #fee2e2; }
```

### Message Avatars
```css
.message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### Layout
```css
.sidebar { width: 260px; }  /* Adjust sidebar width */
.messages { max-width: 800px; }  /* Adjust message width */
```

## Keyboard Shortcuts

- **Enter**: Send message
- **Shift+Enter**: New line in message
- **Cmd/Ctrl+K**: Focus input (future enhancement)

## Browser Compatibility

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile: ⚠️ Responsive but file upload may vary

## API Endpoints Used

- `POST /api/upload` - File upload
- `GET /api/status` - Status polling
- `GET /api/correction-context` - Issue details
- `POST /api/retry-approval` - Retry decision
- `POST /api/user-input` - Metadata submission
- `GET /api/download/nwb` - File download
- `POST /api/reset` - Reset session
- `WS /ws` - WebSocket events

## Screenshots

### Welcome Screen
Clean interface with greeting message and upload prompt.

### File Upload
User selects file → System shows confirmation with action buttons.

### Converting
Real-time status updates with loading indicator.

### Validation Issues
Detailed breakdown of auto-fixable vs user-input-required issues.

### User Input Modal
Dynamic form for collecting missing metadata.

### Completion
Success message with download button.

## Future Enhancements

- [ ] Conversation history in sidebar
- [ ] Markdown support in messages
- [ ] Code syntax highlighting for metadata
- [ ] File preview before upload
- [ ] Progress bar for large files
- [ ] Drag-and-drop file upload zone
- [ ] Export conversation as PDF
- [ ] Dark mode toggle
- [ ] Keyboard shortcuts
- [ ] Multi-file batch conversion

## Troubleshooting

### WebSocket Not Connecting
- Check server is running: `curl http://localhost:8000/api/health`
- Check browser console for errors
- Verify port 8000 is accessible

### Modal Not Showing Form Fields
- Check browser console for JavaScript errors
- Verify API response format from `/api/correction-context`
- Ensure backend logs show "User input required"

### File Upload Fails
- Check file size (<100MB recommended)
- Verify file format (`.bin`, `.dat`, `.continuous`)
- Check server logs: `curl http://localhost:8000/api/logs`

### Messages Not Appearing
- Check browser console for JavaScript errors
- Verify DOM element IDs match JavaScript references
- Try hard refresh (Cmd+Shift+R)

## Development

### Running in Development
```bash
# Terminal 1: Start backend
pixi run serve

# Terminal 2: Serve frontend
cd frontend/public
python -m http.server 3000

# Open: http://localhost:3000/chat-ui.html
```

### Adding New Message Types
```javascript
function addCustomMessage(content) {
  addAssistantMessage(
    '<div class="custom-content">' + content + '</div>',
    [
      { text: 'Action 1', onClick: handler1, variant: 'primary' },
      { text: 'Action 2', onClick: handler2, variant: 'secondary' }
    ]
  );
}
```

### Adding New Status
```css
.status-my-new-status {
  background: #color;
  color: #text-color;
}
```

## Support

For issues or questions:
- Check logs: DevTools Console (F12)
- API health: `curl http://localhost:8000/api/health`
- Reset state: Click "New Conversation"

---

**Enjoy the new conversational interface!** 🎉
