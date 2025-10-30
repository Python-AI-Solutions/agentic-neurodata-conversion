# NWB Conversion Pipeline - Web Frontend

**A modern chat-based web interface for the Multi-Agent NWB Conversion Pipeline**

---

## Features

✨ **Modern Chat Interface**
- Clean, intuitive chatbot-style UI
- Real-time system status monitoring
- Session management sidebar
- Command-based interaction

🎯 **Key Capabilities**
- Start dataset conversions
- Monitor conversion progress
- Check session status
- View active sessions
- System health monitoring

📊 **Live Monitoring**
- MCP server status
- Redis connection status
- Active agents count
- Session progress tracking

---

## Quick Start

### Step 1: Start the MCP Server

```bash
# In terminal 1 - Start all backend services
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
pixi run python scripts/start_all_services.py
```

Wait for "System is ready!" message.

---

### Step 2: Open the Frontend

Simply open `index.html` in your web browser:

**Option A: Double-click**
- Navigate to `frontend/` folder
- Double-click `index.html`

**Option B: From terminal**
```bash
# Windows
start frontend/index.html

# Or use your browser directly
"C:\Program Files\Google\Chrome\Application\chrome.exe" frontend/index.html
```

**Option C: Using a local web server (recommended)**
```bash
# Install a simple http server (one-time)
npm install -g http-server

# Start server in frontend directory
cd frontend
http-server -p 3000

# Open http://localhost:3000 in your browser
```

---

## Using the Chat Interface

### Available Commands

#### Start a Conversion
```
start conversion ./tests/data/synthetic_openephys
```
or
```
convert ./path/to/dataset
```

#### Check Status
```
status <session-id>
```
or
```
check status <session-id>
```

If you have a current session:
```
status
```

#### System Health
```
health
```

#### List Sessions
```
list sessions
```

#### Get Help
```
help
```

---

## Example Workflow

1. **Check System Health**
   ```
   health
   ```
   Response: "System is healthy. 3 agents registered. Redis: connected."

2. **Start a Conversion**
   ```
   start conversion ./tests/data/synthetic_openephys
   ```
   Response: Session ID and initialization status

3. **Check Progress**
   ```
   status abc123...
   ```
   Response: Current workflow stage and progress percentage

4. **View All Sessions**
   ```
   list sessions
   ```
   Sessions also appear in the sidebar

---

## UI Overview

### Header
- **Title**: Application name
- **Status Indicator**: Shows connection status
  - 🟢 Green = Connected
  - 🟡 Yellow = Connecting
  - 🔴 Red = Connection Error

### Sidebar (Left)

**System Status Section:**
- MCP Server status
- Redis connection status
- Number of registered agents

**Active Sessions Section:**
- List of current conversion sessions
- Click any session to view its status

**Quick Actions:**
- Check Health button
- Refresh Sessions button

### Chat Area (Center)

**Chat Messages:**
- Welcome message with quick commands
- Your messages (right side, blue)
- Assistant responses (left side, green)
- System messages (gray)

**Input Area:**
- Text input for commands
- Send button (or press Enter)
- Command hints below input

---

## Customization

### Change API URL

Edit `app.js` line 2:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

Change to your server URL if different.

---

### Modify Colors

Edit `styles.css` root variables:

```css
:root {
    --primary-color: #4F46E5;  /* Main theme color */
    --success-color: #10B981;  /* Success messages */
    --error-color: #EF4444;    /* Error messages */
    /* ... */
}
```

---

## Troubleshooting

### "Connection Error" Status

**Problem**: Red status indicator, cannot connect

**Solution**:
1. Ensure MCP server is running: `pixi run python scripts/start_all_services.py`
2. Check server is on `http://localhost:8000`
3. Verify no firewall blocking localhost
4. Check browser console (F12) for errors

---

### Commands Not Working

**Problem**: Commands don't trigger expected responses

**Solution**:
1. Type `help` to see available commands
2. Check command syntax (case-insensitive)
3. Ensure you include required parameters (like dataset path)
4. Check browser console (F12) for JavaScript errors

---

### CORS Errors

**Problem**: "CORS policy" errors in browser console

**Solution**:
The MCP server has CORS enabled by default. If you still get errors:

1. Make sure you're opening the HTML file properly (not file:// protocol if using fetch)
2. Use a local web server (http-server, Python's http.server, etc.)
3. Check that the MCP server CORS settings allow your origin

---

### Sessions Not Appearing in Sidebar

**Problem**: Sidebar shows "No active sessions"

**Solution**:
1. Start a conversion first
2. Click "Refresh Sessions" button
3. The current API has limited session listing - this is a known limitation

---

## Technical Details

### File Structure

```
frontend/
├── index.html    # Main HTML structure
├── styles.css    # CSS styling
├── app.js        # JavaScript logic
└── README.md     # This file
```

### Dependencies

**None!**

This frontend uses vanilla JavaScript with no external dependencies. It works directly in any modern web browser.

### Browser Compatibility

- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari
- ❌ IE11 (not supported)

### API Endpoints Used

```
GET  /health                              # System health
POST /api/v1/sessions/initialize          # Start conversion
GET  /api/v1/sessions/{id}/status         # Session status
```

---

## Development

### Testing Locally

1. Start backend services
2. Open `index.html` in browser
3. Open browser DevTools (F12)
4. Watch console for logs
5. Test commands in chat

### Making Changes

**HTML**: Edit `index.html` for structure
**Styling**: Edit `styles.css` for appearance
**Logic**: Edit `app.js` for functionality

Refresh browser after changes (Ctrl+F5 for hard refresh).

---

## Future Enhancements

Possible improvements:

- [ ] Real-time progress updates via WebSocket
- [ ] Multiple session management
- [ ] File upload for dataset selection
- [ ] Download conversion results
- [ ] Clarification dialog for user input
- [ ] Conversion history
- [ ] Advanced filtering and search
- [ ] Dark mode toggle
- [ ] Export chat history

---

## Support

**Issues?**
- Check browser console (F12) for errors
- Verify MCP server is running
- Review troubleshooting section
- Check main project README

**Questions?**
- See main project documentation
- Check API documentation at http://localhost:8000/docs

---

## Credits

Built for the Multi-Agent NWB Conversion Pipeline project.

**Technologies:**
- HTML5
- CSS3 (with CSS Grid and Flexbox)
- Vanilla JavaScript (ES6+)
- Fetch API for HTTP requests
