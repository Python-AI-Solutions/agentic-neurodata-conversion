# Test Coverage Improvement Plan
## From 59% to 80% Coverage

**Goal**: Increase test coverage from current 59% to constitutional target of 80%
**Status**: ✅ In Progress
**Started**: 2025-10-16

---

## Current Coverage Baseline

### Overall: 59% (1671 statements, 677 missing)

| File | Current | Target | Priority | Status |
|------|---------|--------|----------|--------|
| **mcp_server.py** | 100% | 100% | ✅ Complete | Perfect |
| **models/*** | 97-100% | 100% | ✅ Complete | Excellent |
| **evaluation_agent.py** | 71% | 80% | 🟡 Medium | Good, needs boost |
| **conversion_agent.py** | 55% | 80% | 🔴 High | Needs work |
| **llm_service.py** | 32%→55% | 80% | 🔴 High | ✅ **Improved!** |
| **main.py** | 50% | 80% | 🔴 High | Needs work |
| **conversation_agent.py** | 48% | 80% | 🔴 High | Needs work |
| **conversational_handler.py** | 13% | 80% | 🔴 Highest | ✅ **Test created!** |

---

## Progress Tracking

### ✅ Completed (Phase 1)

**1. LLM Service Tests** (32% → 55%)
- ✅ Created: `backend/tests/unit/test_llm_service.py`
- ✅ Tests: 23 test cases covering:
  - MockLLMService (default & custom responses)
  - AnthropicLLMService (initialization, completion, structured output)
  - Error handling (empty responses, API errors, invalid JSON)
  - Factory function (create_llm_service)
  - LLMServiceError exception
  - Temperature tuning (0.3 for structured, 0.7 for completion)
  - Markdown code block parsing

**Coverage Improvement**: +23% (32% → 55%)

**2. Conversational Handler Tests**
- ✅ Created: `backend/tests/unit/test_conversational_handler.py`
- ✅ Tests: 15 test cases covering:
  - Initialization with LLM service
  - General query handling in all states (IDLE, CONVERTING, COMPLETED, FAILED)
  - Context summary generation
  - Action suggestions based on state
  - Fallback behavior (no LLM service)
  - Error handling

**Expected Coverage**: 13% → 70%+

---

### 🔄 In Progress (Phase 2)

**3. Conversation Agent Tests** (48% → 80%)
- 📝 File to create: `backend/tests/unit/test_conversation_agent.py`
- 🎯 Focus areas (164 missing lines):
  - `handle_start_conversion` (lines 71-75, 101)
  - `handle_general_query` (lines 1429-1564)
  - `_proactive_issue_detection` (lines 252-386)
  - `_generate_welcome_message` (lines 561-625)
  - Error handling paths
  - State transitions

**Estimated Tests Needed**: ~25 test cases
**Expected Coverage**: 48% → 80%

---

### ⏳ Pending (Phase 3)

**4. Conversion Agent Tests** (55% → 80%)
- 📝 File to create: `backend/tests/unit/test_conversion_agent.py`
- 🎯 Focus areas (106 missing lines):
  - `_detect_format` (lines 151-222) - LLM-first logic
  - `_optimize_conversion_parameters` (lines 483-587)
  - `_narrate_progress` (lines 620-677)
  - `_run_neuroconv_conversion` edge cases
  - Error handling

**Estimated Tests Needed**: ~20 test cases
**Expected Coverage**: 55% → 80%

**5. Main API Tests** (50% → 80%)
- 📝 File to create: `backend/tests/unit/test_api_endpoints.py`
- 🎯 Focus areas (113 missing lines):
  - `/api/chat` endpoint
  - `/api/chat/smart` endpoint
  - `/api/correction-context` endpoint
  - File upload validation edge cases
  - Error responses
  - WebSocket functionality

**Estimated Tests Needed**: ~15 test cases
**Expected Coverage**: 50% → 80%

**6. Evaluation Agent Tests** (71% → 85%)
- 📝 File: Extend existing tests
- 🎯 Focus areas (67 missing lines):
  - `_assess_nwb_quality` (quality scoring, lines 393-572)
  - Error handling in validation
  - Report generation edge cases

**Estimated Tests Needed**: ~10 test cases
**Expected Coverage**: 71% → 85%

**7. Fix Failing Integration Tests**
- 🔧 6 failing tests in `test_conversion_workflow.py`:
  - `test_validation_with_mock_llm`
  - `test_start_conversion_workflow`
  - `test_user_format_selection`
  - `test_auto_fix_extraction`
  - `test_user_input_required_detection`
  - `test_full_workflow_passed_scenario`

---

## Test Strategy

### Unit Test Patterns

**Pattern 1: Agent Methods**
```python
@pytest.mark.asyncio
async def test_agent_method_success():
    """Test successful execution."""
    agent = ConversationAgent(llm_service=MockLLMService())
    state = GlobalState()

    result = await agent.method(params, state)

    assert result is not None
    assert state.status == expected_status
```

**Pattern 2: Error Handling**
```python
@pytest.mark.asyncio
async def test_agent_method_error_handling():
    """Test error is caught and logged."""
    agent = ConversationAgent(llm_service=None)
    state = GlobalState()

    result = await agent.method_that_fails(params, state)

    assert not result.success
    assert any("error" in log.message.lower() for log in state.logs)
```

**Pattern 3: LLM Integration with Mock**
```python
@pytest.mark.asyncio
async def test_llm_integration():
    """Test LLM is called with correct parameters."""
    mock_llm = MockLLMService()
    mock_llm.set_response("test", '{"result": "success"}')

    agent = ConversationAgent(llm_service=mock_llm)
    result = await agent.llm_method("test")

    assert result["result"] == "success"
```

---

## Coverage Calculation

### Current State (59%)
```
Total Statements: 1,671
Missing Coverage: 677
Covered: 994
Coverage: 994/1671 = 59.5%
```

### Target State (80%)
```
Total Statements: 1,671
Required Covered: 1,337 (80% of 1,671)
Current Covered: 994
Statements Needed: 343 more statements
```

### Gap Analysis

**Statements to Cover**: 343
**Current Missing**: 677
**Percentage Improvement Needed**: +21% (59% → 80%)

### By File Priority

| File | Statements Missing | To Cover for 80% | Priority |
|------|-------------------|------------------|----------|
| conversation_agent.py | 164 | 64 needed | 🔴 High |
| main.py | 113 | 45 needed | 🔴 High |
| conversion_agent.py | 106 | 59 needed | 🔴 High |
| conversational_handler.py | 90 | 72 needed | 🔴 Highest |
| evaluation_agent.py | 67 | 17 needed | 🟡 Medium |
| llm_service.py | 32 | ✅ **Improved** | 🟢 Done |
| report_service.py | 37 | 15 needed | 🟡 Medium |
| file_versioning.py | 43 | 11 needed | 🟢 Low |

**Total Prioritized Coverage Needed**: ~343 statements

---

## Estimated Effort

### Time Breakdown

| Phase | Tasks | Tests to Write | Estimated Time |
|-------|-------|----------------|----------------|
| ✅ **Phase 1** | LLM + Handler | 38 tests | ✅ **4 hours (DONE)** |
| 🔄 **Phase 2** | Conversation Agent | 25 tests | 4-5 hours |
| ⏳ **Phase 3** | Conversion Agent | 20 tests | 3-4 hours |
| ⏳ **Phase 4** | Main API | 15 tests | 3 hours |
| ⏳ **Phase 5** | Evaluation + Fixes | 20 tests | 3 hours |

**Total Estimated Time**: 17-20 hours (~2.5 days)
**Completed So Far**: 4 hours (20%)
**Remaining**: 13-16 hours

---

## Implementation Plan

### Day 1 (✅ Partially Complete)
- ✅ Create LLM service tests (4 hours)
- ✅ Create conversational handler tests (1 hour)
- 🔄 Create conversation agent tests (4 hours - IN PROGRESS)

### Day 2 (Planned)
- Create conversion agent tests (4 hours)
- Create main API tests (3 hours)
- Run coverage and identify remaining gaps (1 hour)

### Day 3 (Planned)
- Extend evaluation agent tests (2 hours)
- Fix failing integration tests (3 hours)
- Final coverage verification (1 hour)
- Documentation updates (1 hour)

---

## Success Criteria

### Minimum Requirements
- [ ] Overall coverage ≥ 80%
- [ ] All agents ≥ 80% coverage
- [ ] All services ≥ 80% coverage
- [ ] API endpoints ≥ 80% coverage
- [ ] All integration tests passing
- [ ] No regressions in existing tests

### Stretch Goals
- [ ] Overall coverage ≥ 85%
- [ ] All critical paths 100% covered
- [ ] Error handling 100% covered
- [ ] LLM integration 100% covered

---

## Testing Best Practices Applied

### ✅ Followed
1. **Arrange-Act-Assert** pattern in all tests
2. **Descriptive test names** (what is tested, not how)
3. **Isolated tests** (no dependencies between tests)
4. **Mock external services** (LLM, file system)
5. **Test both success and failure paths**
6. **Async test support** (pytest-asyncio)
7. **Fixtures for reusability** (state, agents, services)

### ✅ Coverage Types
1. **Unit tests**: Individual methods/functions
2. **Integration tests**: Multi-component workflows
3. **Error handling tests**: Exception paths
4. **Edge case tests**: Boundary conditions
5. **Mock tests**: LLM integration without API calls

---

## Current Test Statistics

### Before Improvement
```
Total Tests: 40
Passing: 34
Failing: 6
Coverage: 59%
Test Files: 5
```

### After Phase 1
```
Total Tests: 78 (+38)
Passing: TBD
Failing: TBD
Coverage: 61-63% (estimated)
Test Files: 7 (+2)
```

### Target (After All Phases)
```
Total Tests: 120-130
Passing: 120-130
Failing: 0
Coverage: 80-85%
Test Files: 10-12
```

---

## Dependencies & Blockers

### ✅ Resolved
- Pytest and pytest-asyncio configured
- Mock patterns established
- Fixtures created
- Test data available

### 🔴 Current Blockers
- Some integration tests failing (needs investigation)
- Need toy dataset for certain conversion tests
- Some LLM responses hard to mock (complex structured outputs)

### Solutions
- Fix integration tests after unit tests complete
- Use existing `generate_toy_dataset.py` for test data
- Create comprehensive mock responses library

---

## Next Steps (Immediate)

1. **Complete Phase 2**: Conversation agent tests
2. **Run coverage** after each file to track progress
3. **Document any patterns** discovered during testing
4. **Update this document** with actual coverage numbers

---

## Resources

### Test Files Created
- ✅ `backend/tests/unit/test_llm_service.py` (23 tests)
- ✅ `backend/tests/unit/test_conversational_handler.py` (15 tests)
- 🔄 `backend/tests/unit/test_conversation_agent.py` (IN PROGRESS)
- ⏳ `backend/tests/unit/test_conversion_agent.py` (PENDING)
- ⏳ `backend/tests/unit/test_api_endpoints.py` (PENDING)

### Existing Test Files
- `backend/tests/unit/test_mcp_server.py` (15 tests - 100% coverage)
- `backend/tests/integration/test_api.py` (API integration tests)
- `backend/tests/integration/test_conversion_workflow.py` (Workflow tests)

---

## Metrics Dashboard

### Coverage by Category

```
Models:        97-100% ✅ Excellent
Services:      55-100% 🟡 Good (LLM improved!)
Agents:        48-71%  🔴 Needs Work (Primary Focus)
API:           50%     🔴 Needs Work
Utils:         23%     🟢 Low Priority
```

### Test Distribution

```
Unit Tests:        78 (target: 110)
Integration Tests: 40 (target: 40)
Total Tests:       118 (target: 150)
```

---

**Status**: 🔄 **IN PROGRESS** - Phase 1 Complete, Phase 2 Started

**Last Updated**: 2025-10-16

**Next Milestone**: Complete conversation_agent tests and reach 65% overall coverage
