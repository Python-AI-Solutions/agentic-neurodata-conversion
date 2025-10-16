# Next Steps for Test Coverage - Quick Reference

**Current Coverage:** 42% → **Target:** 80% → **Remaining:** 38 percentage points

---

## 🚀 Quick Start Commands

```bash
# Run all tests with coverage
pixi run pytest backend/tests/unit/ --cov=backend/src --cov-report=term

# Run specific test file
pixi run pytest backend/tests/unit/test_main.py -v

# Run tests excluding known patterns
pixi run pytest backend/tests/unit/ -k "not test_pattern_to_skip"

# Generate HTML coverage report
pixi run pytest backend/tests/unit/ --cov=backend/src --cov-report=html
open htmlcov/index.html
```

---

## ⚡ Priority Tasks (In Order)

### 1. Fix conversation_agent Tests (30 minutes)
**File:** `backend/tests/unit/test_conversation_agent.py`
**Impact:** +5% coverage
**Issue:** 14 tests need fixes

**Quick Fixes Needed:**
```python
# Fix enum values
ConversionStatus.AWAITING_FORMAT_SELECTION  # Wrong
ConversionStatus.IDLE  # Use this instead

ConversionStatus.AWAITING_RETRY_DECISION  # Wrong
ConversionStatus.AWAITING_RETRY_APPROVAL  # Use this instead (maybe)

# Fix method signatures (check actual signatures first)
# _explain_error_to_user(error_info, context, state)  # Actual
# _proactive_issue_detection(input_path, format_name, state)  # Actual
# _generate_status_message(action, context, state)  # Actual
```

**Command to check signatures:**
```bash
grep -A 5 "def _explain_error_to_user\|def _proactive_issue\|def _generate_status" backend/src/agents/conversation_agent.py
```

---

### 2. Create main.py API Tests (3-4 hours)
**File:** `backend/tests/unit/test_main.py` (create new)
**Impact:** +18% coverage (227 lines)
**Current:** 0%

**Test Structure:**
```python
"""Unit tests for FastAPI main application."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from api.main import app

class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test GET /health returns 200."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

class TestUploadEndpoint:
    """Tests for file upload endpoint."""

    def test_upload_file_success(self):
        """Test POST /upload with valid file."""
        client = TestClient(app)
        files = {"file": ("test.bin", b"test data", "application/octet-stream")}
        response = client.post("/upload", files=files)
        assert response.status_code == 200

class TestStatusEndpoint:
    """Tests for status endpoint."""

    def test_get_status(self):
        """Test GET /status returns current state."""
        client = TestClient(app)
        response = client.get("/status")
        assert response.status_code == 200

class TestDownloadEndpoint:
    """Tests for download endpoint."""

    def test_download_file(self):
        """Test GET /download/{file_id}."""
        client = TestClient(app)
        # Mock file existence
        response = client.get("/download/test.nwb")
        # Assert appropriate response

class TestWebSocketEndpoint:
    """Tests for WebSocket connections."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection and messages."""
        # Use TestClient's websocket_connect
        pass
```

**Key Areas:**
- Health check endpoint
- File upload handling
- Status queries
- Download endpoints
- WebSocket connections
- Error handling (400, 404, 500)
- Request validation
- Response formatting

---

### 3. Create evaluation_agent Tests (3-4 hours)
**File:** `backend/tests/unit/test_evaluation_agent.py` (create new)
**Impact:** +17% coverage (209 lines)
**Current:** 9%

**Test Structure:**
```python
"""Unit tests for evaluation agent."""
import pytest
from agents.evaluation_agent import EvaluationAgent
from models import GlobalState, ValidationStatus
from services.llm_service import MockLLMService

class TestEvaluationAgentInitialization:
    """Tests for agent initialization."""

class TestNWBValidation:
    """Tests for NWB Inspector integration."""

    @pytest.mark.asyncio
    async def test_validate_nwb_file_success(self):
        """Test successful NWB validation."""
        pass

    @pytest.mark.asyncio
    async def test_validate_nwb_file_with_issues(self):
        """Test validation with issues found."""
        pass

class TestQualityScoring:
    """Tests for quality score calculation."""

    def test_calculate_quality_score_perfect(self):
        """Test quality score for perfect file."""
        pass

    def test_calculate_quality_score_with_issues(self):
        """Test quality score with issues."""
        pass

class TestReportGeneration:
    """Tests for validation report generation."""

    @pytest.mark.asyncio
    async def test_generate_report_json(self):
        """Test generating JSON report."""
        pass

    @pytest.mark.asyncio
    async def test_generate_report_pdf(self):
        """Test generating PDF report."""
        pass

class TestLLMAnalysis:
    """Tests for LLM-based validation analysis."""

    @pytest.mark.asyncio
    async def test_analyze_validation_with_llm(self):
        """Test LLM analysis of validation results."""
        pass
```

**Key Areas:**
- NWB Inspector validation (66 checks)
- Quality score calculation
- Report generation (JSON/PDF)
- LLM-based analysis
- Proactive issue detection
- Correction suggestions
- Error categorization

---

### 4. Complete Smaller Files (2 hours)
**Impact:** +5% coverage combined

#### A. report_service.py (16% → 60%)
```python
# Test PDF generation
# Test JSON report formatting
# Test report templates
# Test error handling
```

#### B. prompt_service.py (29% → 60%)
```python
# Test YAML template loading
# Test prompt formatting
# Test variable substitution
# Test template caching
```

#### C. file_versioning.py (23% → 60%)
```python
# Test file version tracking
# Test checksum calculation
# Test version comparison
# Test file history
```

---

## 📋 Testing Checklist

### Before Starting New Tests
- [ ] Read the actual implementation file
- [ ] Check method signatures with grep
- [ ] Identify all public methods
- [ ] List all edge cases
- [ ] Check for existing integration tests

### While Writing Tests
- [ ] Use proper fixtures for setup
- [ ] Mock external dependencies (LLM, files, APIs)
- [ ] Test both success and error paths
- [ ] Use descriptive test names
- [ ] Add docstrings to tests
- [ ] Follow Arrange-Act-Assert pattern

### After Writing Tests
- [ ] Run tests and verify they pass
- [ ] Check coverage improvement
- [ ] Fix any failing tests immediately
- [ ] Update documentation
- [ ] Commit with clear message

---

## 🔍 Common Patterns

### 1. Mock LLM Service
```python
@pytest.fixture
def llm_service():
    mock_llm = MockLLMService()
    mock_llm.set_response("key", '{"result": "data"}')
    return mock_llm
```

### 2. Temporary Files
```python
@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

### 3. Mock Async Methods
```python
async def mock_send_message(msg):
    return MCPResponse.success_response(
        reply_to=msg.message_id,
        result={"status": "success"}
    )
mcp_server.send_message = mock_send_message
```

### 4. FastAPI Testing
```python
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.get("/endpoint")
assert response.status_code == 200
```

---

## 📊 Coverage Tracking

### Check Overall Coverage
```bash
pixi run pytest backend/tests/unit/ --cov=backend/src --cov-report=term | grep "TOTAL"
```

### Check Specific File Coverage
```bash
pixi run pytest backend/tests/unit/ --cov=backend/src/agents/conversation_agent.py --cov-report=term
```

### Identify Missing Lines
```bash
pixi run pytest backend/tests/unit/ --cov=backend/src --cov-report=term-missing | grep "conversation_agent"
```

---

## 🎯 Coverage Goals

| File | Current | Target | Status |
|------|---------|--------|--------|
| conversation_agent.py | 18% | 80% | 🟡 In Progress |
| main.py | 0% | 80% | 🔴 Not Started |
| evaluation_agent.py | 9% | 80% | 🔴 Not Started |
| report_service.py | 16% | 60% | 🔴 Not Started |
| prompt_service.py | 29% | 60% | 🟡 Partially Done |
| file_versioning.py | 23% | 60% | 🟡 Partially Done |

**Target:** 80% overall coverage
**Current:** 42%
**Remaining:** 38 percentage points

---

## 💡 Tips for Fast Progress

### 1. Start with Happy Path Tests
- Test successful cases first
- Add error cases later
- This builds coverage fastest

### 2. Use Existing Tests as Templates
- Copy structure from test_llm_service.py
- Adapt patterns from test_conversion_agent.py
- Reuse fixtures where possible

### 3. Mock Aggressively
- Don't test external dependencies
- Use MockLLMService for all LLM calls
- Mock file operations when possible
- Mock MCP server responses

### 4. Test in Batches
- Write 5-10 tests
- Run and verify
- Fix any failures
- Repeat

### 5. Leverage Code Coverage Reports
- Run coverage after each batch
- Focus on uncovered lines
- Target largest gaps first

---

## 🐛 Known Issues to Fix

### conversation_agent.py Tests
- Fix 3 enum value errors
- Fix 9 method signature errors
- Add better mocking for _run_conversion workflow

### General
- Some Pydantic deprecation warnings (non-critical)
- 6 integration tests still failing (separate issue)

---

## 📝 Documentation Updates Needed

After reaching 80%:
- [ ] Update README with test coverage badge
- [ ] Update TEST_COVERAGE_FINAL_SUMMARY.md
- [ ] Create TESTING_GUIDE.md for contributors
- [ ] Document any remaining coverage gaps
- [ ] Update constitution.md (if needed)

---

## 🎓 Resources

- **pytest docs:** https://docs.pytest.org/
- **pytest-asyncio:** https://pytest-asyncio.readthedocs.io/
- **FastAPI testing:** https://fastapi.tiangolo.com/tutorial/testing/
- **unittest.mock:** https://docs.python.org/3/library/unittest.mock.html

---

## ✅ Success Criteria

Tests are complete when:
- [ ] Overall coverage ≥ 80%
- [ ] All unit tests passing
- [ ] No critical code paths untested
- [ ] Error handling thoroughly tested
- [ ] Documentation updated
- [ ] CI/CD pipeline passing

**Estimated Time to Complete:** 8-10 hours of focused work

---

**Last Updated:** 2025-10-16
**Next Review:** After main.py and evaluation_agent.py tests completed
