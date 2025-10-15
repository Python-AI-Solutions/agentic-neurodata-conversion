# Quickstart Guide 🚀

Get up and running with the Agentic Neurodata Conversion system in 5 minutes.

## Prerequisites Check

Before starting, ensure you have:

- ✅ [Pixi](https://pixi.sh/) installed
- ✅ Git
- ✅ A modern web browser
- ⚠️ (Optional) Anthropic API key for LLM features

Install Pixi if needed:
```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

## Step 1: Setup (2 minutes)

```bash
# Navigate to project directory
cd agentic-neurodata-conversion-14

# Install all dependencies
pixi install

# Generate test dataset (creates ~10MB of toy SpikeGLX data)
pixi run generate-fixtures
```

## Step 2: Start the Backend (30 seconds)

```bash
# Start the API server
pixi run dev
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

✅ Backend is running at http://localhost:8000

Test it:
```bash
curl http://localhost:8000/api/health
```

## Step 3: Open the Web UI (30 seconds)

**Option A: Using Python's built-in server**

Open a new terminal:
```bash
cd frontend/public
python -m http.server 3000
```

Then open http://localhost:3000 in your browser.

**Option B: Open the file directly**

Just open `frontend/public/index.html` in your browser (file:// URL).
Note: WebSocket features may not work with file:// URLs.

## Step 4: Convert Your First File (1 minute)

### Using the Web UI

1. **Drop a file** onto the upload area (or click to browse)
2. **Click "Start Conversion"**
3. **Watch the status** update in real-time
4. **Download** when complete

### Using the Test Dataset

Use the generated toy dataset:

```bash
# Via API
curl -X POST http://localhost:8000/api/upload \
  -F "file=@backend/tests/fixtures/toy_spikeglx/toy_recording.ap.bin" \
  -F 'metadata={"session_description": "Quickstart test"}'

# Check status
curl http://localhost:8000/api/status

# View logs
curl http://localhost:8000/api/logs | python -m json.tool
```

## Step 5: Understanding What Happened

The system just:

1. **Detected** the file format (SpikeGLX)
2. **Converted** it to NWB using NeuroConv
3. **Validated** the NWB file with NWB Inspector
4. **Reported** results

All orchestrated by three specialized agents:
- 🔄 **Conversion Agent** - Format detection + conversion
- ✅ **Evaluation Agent** - Validation + quality checks
- 💬 **Conversation Agent** - Workflow orchestration

## Next Steps

### Enable LLM Features (Optional)

For AI-powered correction analysis:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
pixi run dev  # Restart the server
```

Now validation failures will include intelligent suggestions for fixes.

### Run the Tests

```bash
# Quick test
pixi run test-unit

# Full test suite
pixi run test

# With coverage
pixi run pytest backend/tests -v --cov=backend/src
```

### Explore the API

Interactive API docs at: http://localhost:8000/docs

Key endpoints:
- `POST /api/upload` - Start conversion
- `GET /api/status` - Check progress
- `GET /api/logs` - View detailed logs
- `GET /api/download/nwb` - Get converted file
- `POST /api/reset` - Start fresh

### Try Your Own Data

Replace the test data with your actual neurodata files:

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/your/recording.bin" \
  -F 'metadata={"session_description": "My experiment", "experimenter": ["Your Name"]}'
```

## Troubleshooting

### Port 8000 already in use?

Change the port in `pixi.toml`:
```toml
dev = "uvicorn backend.src.api.main:app --reload --host 0.0.0.0 --port 8001"
```

### Can't find dependencies?

Re-run the install:
```bash
pixi clean
pixi install
```

### Test dataset missing?

Generate it:
```bash
pixi run generate-fixtures
```

### Browser CORS errors?

Make sure you're accessing the frontend through http://localhost:3000, not file://.

### Conversion fails?

Check the logs:
```bash
curl http://localhost:8000/api/logs | python -m json.tool
```

Reset and try again:
```bash
curl -X POST http://localhost:8000/api/reset
```

## Understanding the Workflow

```
┌─────────────┐
│   Upload    │
│    File     │
└──────┬──────┘
       │
       ▼
┌─────────────┐    ┌──────────────┐
│   Detect    │───▶│ User Selects │ (if ambiguous)
│   Format    │    │   Format     │
└──────┬──────┘    └──────┬───────┘
       │                  │
       │◀─────────────────┘
       ▼
┌─────────────┐
│   Convert   │
│   to NWB    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Validate   │
│   NWB File  │
└──────┬──────┘
       │
       ▼
    ┌──┴──┐
    │Valid?│
    └─┬─┬─┘
      │ │
  Yes │ │ No
      │ │
      ▼ ▼
   ┌────┴─────┐    ┌───────────┐
   │ Download │    │   Retry   │──┐
   │   File   │    │ Approval? │  │
   └──────────┘    └─────┬─────┘  │
                         │        │
                     Yes │        │ No
                         │        │
                         ▼        ▼
                   ┌──────────┐ ┌──────┐
                   │ Analyze  │ │ Fail │
                   │  & Retry │ └──────┘
                   └────┬─────┘
                        │
                        │ (back to Convert)
                        └───────────────────┐
                                           │
                                           ▼
```

## Common Use Cases

### 1. Batch Conversion

The MVP supports single conversions. For batch processing:

```bash
for file in data/*.bin; do
    curl -X POST http://localhost:8000/api/reset
    curl -X POST http://localhost:8000/api/upload -F "file=@$file"
    # Wait for completion
    sleep 10
    curl http://localhost:8000/api/download/nwb -o "${file%.bin}.nwb"
done
```

### 2. Programmatic Access

```python
import requests

# Upload
with open('data.bin', 'rb') as f:
    files = {'file': f}
    data = {'metadata': '{"session_description": "Test"}'}
    r = requests.post('http://localhost:8000/api/upload', files=files, data=data)

# Poll status
import time
while True:
    r = requests.get('http://localhost:8000/api/status')
    status = r.json()['status']
    if status in ['completed', 'failed']:
        break
    time.sleep(1)

# Download
if status == 'completed':
    r = requests.get('http://localhost:8000/api/download/nwb')
    with open('output.nwb', 'wb') as f:
        f.write(r.content)
```

### 3. Custom Metadata

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@data.bin" \
  -F 'metadata={
    "session_description": "Detailed experiment description",
    "experimenter": ["John Doe", "Jane Smith"],
    "institution": "University Lab",
    "lab": "Neuroscience Lab",
    "session_start_time": "2025-01-15T10:00:00",
    "subject": {
      "subject_id": "mouse001",
      "age": "P90D",
      "species": "Mus musculus"
    }
  }'
```

## What's Next?

- 📖 Read the full [README.md](README.md)
- 🏗️ Explore the architecture in `specs/001-agentic-neurodata-conversion/`
- 🧪 Run the test suite: `pixi run test`
- 🔧 Customize the agents in `backend/src/agents/`
- 📊 Check the API docs: http://localhost:8000/docs

## Need Help?

- Check the logs: `curl http://localhost:8000/api/logs`
- Read the constitution: `.specify/memory/constitution.md`
- Review the tasks: `specs/001-agentic-neurodata-conversion/tasks.md`
- Open an issue on GitHub

---

**You're all set! Start converting neurodata to NWB with AI assistance.** 🎉
