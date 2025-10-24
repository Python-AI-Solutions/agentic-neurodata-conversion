# Demo Scripts

This directory contains demonstration scripts for the Multi-Agent NWB Conversion Pipeline.

---

## Quick Setup (First Time)

Before running any demo for the first time:

1. **Copy the .env file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your API key to .env:**
   ```bash
   # Open .env in your editor and replace the placeholder:
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   ```

3. **For full demos, start Redis:**
   ```bash
   # See Redis Setup section below for platform-specific instructions
   ```

That's it! The scripts will automatically load your API key from the `.env` file.

---

## Quick Start: Run Full Demo

To run the complete pipeline and generate a real NWB file:

```bash
python scripts/run_full_demo.py
```

This script will:
1. ✓ Check if Redis is running (provides setup instructions if not)
2. ✓ Prompt for your LLM API key (Anthropic or OpenAI)
3. ✓ Start the MCP server automatically
4. ✓ Run the complete pipeline with test data
5. ✓ Generate a real NWB file
6. ✓ Show validation results

### Prerequisites

**Required:**
- Redis server running on localhost:6379
- Anthropic API key OR OpenAI API key

**Redis Setup (Choose one method):**

**Windows:**
```bash
# Option 1: WSL
wsl sudo service redis-server start

# Option 2: Docker
docker run -d -p 6379:6379 redis:alpine

# Option 3: Download Windows build
# https://github.com/microsoftarchive/redis/releases
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Docker (All Platforms):**
```bash
docker run -d -p 6379:6379 redis:alpine
```

### API Keys

**Recommended: Use a .env file**

1. Copy the example .env file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```bash
   # For Anthropic Claude (recommended)
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

   # OR for OpenAI
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. The scripts will automatically load your API key from the .env file

**Alternative: Environment variables or manual entry**

You can also:
1. Set environment variables before running:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   # OR
   export OPENAI_API_KEY="sk-..."
   ```

2. Enter the key when prompted by the script (run_full_demo.py only)

**Get API Keys:**
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys

**Note:** The `.env` file is gitignored for security, so your API keys won't be committed to version control.

### Output

After running, you'll find:

```
demo_output/
├── nwb_files/
│   └── {session_id}.nwb          # Generated NWB file (HDF5 format)
├── reports/
│   └── {session_id}_validation.json  # Validation report
└── sessions/
    └── {session_id}.json         # Session context
```

---

## Alternative Demos

### Mock Demo (No Redis/API Keys Required)

If you want to see the information flow without setting up Redis or API keys:

```bash
python scripts/demo_mock_pipeline.py
```

This shows a simulated run with mock data, demonstrating:
- All 5 phases of the pipeline
- Information flow between agents
- Data structures at each step
- No actual NWB file generation

### Standalone Demo (Requires API Keys, No Redis)

If you want to use filesystem-only mode (no Redis):

```bash
python scripts/demo_full_pipeline_standalone.py
```

**Requirements:**
- API key in .env file (see [API Keys](#api-keys) section above)
- No Redis required

### Full Pipeline Demo (Requires Redis + API Keys)

For a detailed view of the pipeline with Redis storage:

```bash
python scripts/demo_full_pipeline.py
```

**Requirements:**
- Redis running on localhost:6379
- API key in .env file (see [API Keys](#api-keys) section above)

---

## Script Comparison

| Script | Redis Required | API Key Required | .env Support | Generates Real NWB | Best For |
|--------|----------------|------------------|--------------|-------------------|----------|
| `run_full_demo.py` | ✓ Yes | ✓ Yes (.env or prompt) | ✓ Yes | ✓ Yes | **Production-like demo** |
| `demo_full_pipeline.py` | ✓ Yes | ✓ Yes (.env only) | ✓ Yes | ✓ Yes | **Detailed pipeline view** |
| `demo_full_pipeline_standalone.py` | ✗ No | ✓ Yes (.env only) | ✓ Yes | ✓ Yes | **Testing without Redis** |
| `demo_mock_pipeline.py` | ✗ No | ✗ No | ✗ N/A | ✗ No | **Understanding the flow** |

---

## Example Run

```bash
$ python scripts/run_full_demo.py

================================================================================
             Multi-Agent NWB Conversion Pipeline - Full Demo
                      Real Execution with Redis + LLM
================================================================================

[18:00:00.000] >> Checking Redis connection...
  [OK] Redis is running

================================================================================
                           LLM API Configuration
================================================================================

Enter your API key: sk-ant-api03-xxxxx...
[OK] Detected Anthropic API key

Using test dataset: ./tests/data/synthetic_openephys
Output directory: ./demo_output/

Press Enter to start the demo...

[18:00:05.123] >> Setting Up Output Directories
  -> Created: demo_output
  -> Created: demo_output/sessions
  -> Created: demo_output/nwb_files
  -> Created: demo_output/reports

[18:00:05.234] >> Starting MCP Server
  -> Using Anthropic Claude API
  -> Waiting for server to start...
  [OK] MCP Server started successfully
     Server URL: http://localhost:8000

[18:00:08.456] >> Sending HTTP Request
     POST http://localhost:8000/api/v1/sessions/initialize
  [OK] Session initialized successfully
     Session ID: session-abc123...
     Workflow Stage: initialized

[18:00:08.567] >> Monitoring Pipeline Progress
  -> Initializing session...
  -> ConversationAgent: Extracting metadata from dataset...
  -> ConversionAgent: Converting to NWB format...
  -> EvaluationAgent: Validating NWB file...
  -> Pipeline completed successfully!
  [OK] All agents completed their work

[18:00:45.789] >> Fetching Final Results
  [OK] Results retrieved successfully

================================================================================
                              FINAL RESULTS
================================================================================

Pipeline Summary:
  Session ID: session-abc123...
  Final Stage: completed
  Overall Status: passed_with_warnings

Generated NWB File:
  Path: ./demo_output/nwb_files/session-abc123.nwb
  Size: 1.82 MB
  [OK] NWB file successfully created!

Validation Report:
  Path: ./demo_output/reports/session-abc123_validation.json
  Metadata Completeness: 80/100
  Best Practices Score: 95/100
  Issues Found:
    - Critical: 0
    - Violations: 1
    - Suggestions: 2

Validation Summary (LLM-Generated):
  The NWB file passed validation with minor suggestions. All required
  fields are present and the file structure is correct. Consider adding
  institution and device metadata for better compliance.

================================================================================
                        DEMO COMPLETED SUCCESSFULLY!
================================================================================

Generated files:
  - NWB File: ./demo_output/nwb_files/*.nwb
  - Validation Report: ./demo_output/reports/*.json
  - Session Context: ./demo_output/sessions/*.json
```

---

## Troubleshooting

### "Redis is not running"
- Make sure Redis server is started
- Test with: `redis-cli ping` (should return "PONG")
- Check port 6379 is not blocked by firewall

### "No API key found"
- Set environment variable: `export ANTHROPIC_API_KEY="your-key"`
- Or enter key when prompted by the script

### "Dataset not found"
- Make sure you're running from the project root directory
- The test dataset should be at: `./tests/data/synthetic_openephys/`

### "Server failed to start"
- Check if port 8000 is already in use
- Try: `lsof -i :8000` (Unix) or `netstat -ano | findstr :8000` (Windows)
- Kill any existing process using port 8000

### "Timeout waiting for completion"
- Check server logs for errors
- Ensure LLM API key has sufficient credits
- Check network connectivity to LLM API

---

## For More Information

- **Complete Documentation**: [../docs/INFORMATION_FLOW.md](../docs/INFORMATION_FLOW.md)
- **Architecture**: [../docs/architecture/](../docs/architecture/)
- **Test Suite**: Run `pixi run pytest tests/e2e/test_full_pipeline.py -v`

---

## Advanced Usage

### Custom Dataset

To use your own OpenEphys dataset:

```python
# Edit run_full_demo.py, change this line:
dataset_path = "./tests/data/synthetic_openephys"
# To:
dataset_path = "/path/to/your/openephys/data"
```

### Different Output Directory

```python
# Edit run_full_demo.py constructor:
self.output_base = Path("./demo_output")
# To:
self.output_base = Path("/path/to/output")
```

### Using Different Port

```python
# Edit run_full_demo.py:
self.server_url = "http://localhost:8000"
# To:
self.server_url = "http://localhost:9000"

# And update the uvicorn config:
port=8000  # Change to your port
```

---

## Contributing

To add a new demo script:
1. Follow the naming convention: `demo_*.py` or `run_*.py`
2. Add documentation to this README
3. Include error handling and user-friendly messages
4. Test on multiple platforms (Windows, macOS, Linux)
