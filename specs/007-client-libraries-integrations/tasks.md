# Tasks: Client Libraries and Integrations

**Input**: Design documents from `/specs/007-client-libraries-integrations/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Tech stack: Python 3.8-3.12, MCP SDK, Click, Pydantic, pytest
   → Structure: Single project (src/neuroconv_client/)
2. Load design documents:
   → data-model.md: 10 models extracted
   → contracts/: 4 contract files (convert, query_agent, session, health)
   → quickstart.md: 11 test scenarios
3. Generate tasks by category:
   → Setup: 5 tasks (project init, dependencies, linting)
   → Contract Tests: 4 tasks (one per contract file)
   → Integration Tests: 6 tasks (from quickstart scenarios)
   → Models: 4 tasks (config, request/response, progress, error)
   → MCP Protocol: 4 tasks (protocol, transport, streaming, retry)
   → Client: 3 tasks (client class, sync/async APIs)
   → CLI: 5 tasks (main app, commands, formatters)
   → Testing Utilities: 3 tasks (mock server, fixtures)
   → Polish: 8 tasks (unit tests, docs, validation)
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Tests before implementation (TDD)
5. Total tasks: 42 (numbered T001-T042)
6. Parallel tasks: 25 marked [P]
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/neuroconv_client/`, `tests/` at repository root
- All paths are relative to repository root: `C:/Users/shahh/Projects/agentic-neurodata-conversion-2/`

---

## Phase 3.1: Setup

- [ ] T001 Create project structure with directories: src/neuroconv_client/{__init__.py,client.py,config.py,mcp/,models/,cli/,utils/,testing/}, tests/{unit/,integration/,contract/,conftest.py}
- [ ] T002 Initialize Python package with setup.py and pyproject.toml (dependencies: mcp>=0.1.0, pydantic>=2.0.0, click>=8.0.0, aiohttp>=3.8.0, pyyaml>=6.0, pytest>=7.0.0, pytest-asyncio>=0.21.0, pytest-mock>=3.10.0, pytest-cov>=4.0.0)
- [ ] T003 [P] Configure ruff linting in pyproject.toml (target-version = py38, line-length = 100, select = ["E", "F", "I", "N", "W"])
- [ ] T004 [P] Configure mypy type checking in pyproject.toml (python_version = 3.8, strict = true, warn_return_any = true)
- [ ] T005 [P] Create .github/workflows/test.yml for CI/CD (Python 3.8-3.12 matrix, run pytest, ruff check, mypy)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (from contracts/)

- [ ] T006 [P] Contract test for convert operation in tests/contract/test_convert_contract.py (validate JSON-RPC 2.0 request/response schema, streaming progress format, error codes)
- [ ] T007 [P] Contract test for query_agent operation in tests/contract/test_query_agent_contract.py (validate agent types, request/response schema, session context)
- [ ] T008 [P] Contract test for session operations in tests/contract/test_session_contract.py (create_session, get_history, add_message, delete_session)
- [ ] T009 [P] Contract test for health_check operation in tests/contract/test_health_contract.py (validate health status response, server info)

### Integration Tests (from quickstart.md scenarios)

- [ ] T010 [P] Integration test basic synchronous conversion in tests/integration/test_basic_conversion.py (test convert() method, validate ConversionResponse, check success/failure paths)
- [ ] T011 [P] Integration test async streaming conversion in tests/integration/test_async_streaming.py (test convert_async() with AsyncGenerator, validate progress updates, check stage transitions)
- [ ] T012 [P] Integration test session management in tests/integration/test_session_management.py (test create_session, get_session_history, session context in queries)
- [ ] T013 [P] Integration test batch processing in tests/integration/test_batch_processing.py (test BatchConfig with parallel=True/False, checkpoint/resume, error handling)
- [ ] T014 [P] Integration test error handling in tests/integration/test_error_handling.py (test ConnectionError, ValidationError, ServerError with retry logic)
- [ ] T015 [P] Integration test CLI commands in tests/integration/test_cli_commands.py (test convert, batch, query, session, health commands with various flags)

## Phase 3.3: Core Implementation - Models (ONLY after tests are failing)

- [ ] T016 [P] Implement MCPConfig, ServerConfig, RetryConfig, LoggingConfig in src/neuroconv_client/config.py (Pydantic models with validation, default values, field validators)
- [ ] T017 [P] Implement ConversionRequest, ConversionResponse, ConversionMetrics, ValidationResult, DataFormat, ConversionStatus enums in src/neuroconv_client/models/request.py and src/neuroconv_client/models/response.py (path validation, .nwb extension check, overwrite logic)
- [ ] T018 [P] Implement ConversionProgress, ProgressUpdate, ConversionStage in src/neuroconv_client/models/progress.py (streaming model with percent_complete 0-100%, stage transitions, is_complete property)
- [ ] T019 [P] Implement ErrorResponse, ErrorCode, MCPException, ConnectionError, ValidationError, ServerError in src/neuroconv_client/utils/errors.py (JSON-RPC error codes, structured error model with suggestions, custom exceptions)

## Phase 3.4: Core Implementation - MCP Protocol

- [ ] T020 Implement JSON-RPC 2.0 protocol handler in src/neuroconv_client/mcp/protocol.py (encode_request, decode_response, handle_error, validate_jsonrpc)
- [ ] T021 Implement stdio transport layer in src/neuroconv_client/mcp/transport.py (subprocess.Popen for server process, stdin/stdout communication, process lifecycle management)
- [ ] T022 Implement streaming response handler in src/neuroconv_client/mcp/streaming.py (AsyncGenerator for progress updates, backpressure handling with asyncio.Queue, chunk parsing)
- [ ] T023 Implement retry logic with exponential backoff in src/neuroconv_client/utils/retry.py (retry decorator, RetryConfig integration, max_attempts, backoff_factor, max_delay)

## Phase 3.5: Core Implementation - Client

- [ ] T024 Implement MCPClient base class in src/neuroconv_client/client.py (__init__, __aenter__, __aexit__, connect, disconnect, health_check, connection state management with asyncio.Lock)
- [ ] T025 Implement conversion methods in src/neuroconv_client/client.py (convert_async with streaming, get_conversion_result, synchronous convert wrapper with progress_callback)
- [ ] T026 Implement agent and session methods in src/neuroconv_client/client.py (query_agent, create_session, get_session_history, add_message, delete_session)

## Phase 3.6: Core Implementation - CLI

- [ ] T027 Implement Click application entry point in src/neuroconv_client/cli/main.py (main group, global options: --verbose, --log-level, --config, version callback)
- [ ] T028 [P] Implement convert command in src/neuroconv_client/cli/commands/convert.py (arguments: input_path, output_path; options: --format, --validate, --overwrite, --metadata)
- [ ] T029 [P] Implement batch command in src/neuroconv_client/cli/commands/batch.py (argument: config_file; options: --parallel, --workers, --stop-on-error, --resume)
- [ ] T030 [P] Implement query, session, health commands in src/neuroconv_client/cli/commands/query.py, src/neuroconv_client/cli/commands/session.py, src/neuroconv_client/cli/commands/health.py (query: agent, query_text; session: create, history, delete; health: basic check)
- [ ] T031 [P] Implement output formatters in src/neuroconv_client/cli/formatting.py (format_json, format_yaml, format_table, format_text with click.echo)
- [ ] T032 [P] Implement progress indicators in src/neuroconv_client/cli/progress.py (ProgressBar class using click.progressbar, Spinner, Dots with update/finish methods)

## Phase 3.7: Integration & Testing Utilities

- [ ] T033 [P] Implement MockMCPServer for testing in src/neuroconv_client/testing/mock_server.py (simulated MCP server, predefined responses, configurable delays/errors)
- [ ] T034 [P] Implement test fixtures in tests/conftest.py (mock_server fixture, temp_files fixture, sample_conversion_request fixture, client fixture)
- [ ] T035 [P] Implement logging configuration in src/neuroconv_client/utils/logging.py (setup_logging function, LoggingConfig support, text/json formatters, file output)

## Phase 3.8: Polish - Unit Tests

- [ ] T036 [P] Unit tests for MCPConfig and validation in tests/unit/test_config.py (test default values, field validators, timeout ranges, retry limits)
- [ ] T037 [P] Unit tests for ConversionRequest/Response models in tests/unit/test_models.py (path validation, .nwb extension, overwrite check, enum values)
- [ ] T038 [P] Unit tests for protocol handler in tests/unit/mcp/test_protocol.py (JSON-RPC encoding/decoding, error handling, schema validation)
- [ ] T039 [P] Unit tests for retry logic in tests/unit/utils/test_retry.py (backoff calculation, max attempts, exponential delays, retry conditions)
- [ ] T040 [P] Unit tests for CLI formatters in tests/unit/cli/test_formatting.py (JSON output, YAML output, table rendering, text formatting)

## Phase 3.9: Polish - Documentation & Validation

- [ ] T041 [P] Create API documentation in docs/api/ (client.md with MCPClient reference, models.md with all Pydantic models, cli.md with command reference)
- [ ] T042 Run all tests and validate coverage ≥85% (pytest --cov=src/neuroconv_client --cov-report=term-missing, validate all contract tests pass, validate integration tests with MockMCPServer, check type checking with mypy --strict)

---

## Dependencies

### Core Flow
- **Setup (T001-T005)** blocks everything
- **Contract Tests (T006-T009)** and **Integration Tests (T010-T015)** block implementation
- **Models (T016-T019)** block protocol, client, CLI
- **Protocol (T020-T023)** blocks client implementation
- **Client (T024-T026)** blocks CLI implementation
- **CLI (T027-T032)** requires client
- **Unit Tests (T036-T040)** require implementation
- **Documentation (T041-T042)** runs last

### Detailed Dependencies
```
T001-T005 (Setup)
    ├─> T006-T009 (Contract Tests) [P]
    ├─> T010-T015 (Integration Tests) [P]
    └─> T016-T019 (Models) [P]
            ├─> T020-T023 (MCP Protocol)
            │       └─> T024-T026 (Client)
            │               └─> T027-T032 (CLI) [P]
            │                       └─> T041-T042 (Docs & Validation)
            └─> T033-T035 (Testing Utilities) [P]
                    └─> T036-T040 (Unit Tests) [P]
```

## Parallel Execution Examples

### Phase 3.1 Setup (Parallel: 3 tasks)
```bash
# Launch T003, T004, T005 together after T001-T002:
Task: "Configure ruff linting in pyproject.toml"
Task: "Configure mypy type checking in pyproject.toml"
Task: "Create .github/workflows/test.yml for CI/CD"
```

### Phase 3.2 Tests First (Parallel: 10 tasks)
```bash
# Launch all contract tests together (T006-T009):
Task: "Contract test for convert operation in tests/contract/test_convert_contract.py"
Task: "Contract test for query_agent operation in tests/contract/test_query_agent_contract.py"
Task: "Contract test for session operations in tests/contract/test_session_contract.py"
Task: "Contract test for health_check operation in tests/contract/test_health_contract.py"

# Launch all integration tests together (T010-T015):
Task: "Integration test basic synchronous conversion in tests/integration/test_basic_conversion.py"
Task: "Integration test async streaming conversion in tests/integration/test_async_streaming.py"
Task: "Integration test session management in tests/integration/test_session_management.py"
Task: "Integration test batch processing in tests/integration/test_batch_processing.py"
Task: "Integration test error handling in tests/integration/test_error_handling.py"
Task: "Integration test CLI commands in tests/integration/test_cli_commands.py"
```

### Phase 3.3 Models (Parallel: 4 tasks)
```bash
# Launch T016-T019 together:
Task: "Implement MCPConfig, ServerConfig, RetryConfig, LoggingConfig in src/neuroconv_client/config.py"
Task: "Implement ConversionRequest, ConversionResponse in src/neuroconv_client/models/"
Task: "Implement ConversionProgress, ProgressUpdate in src/neuroconv_client/models/progress.py"
Task: "Implement ErrorResponse, MCPException in src/neuroconv_client/utils/errors.py"
```

### Phase 3.6 CLI (Parallel: 4 tasks)
```bash
# Launch T028-T032 together after T027:
Task: "Implement convert command in src/neuroconv_client/cli/commands/convert.py"
Task: "Implement batch command in src/neuroconv_client/cli/commands/batch.py"
Task: "Implement query, session, health commands"
Task: "Implement output formatters in src/neuroconv_client/cli/formatting.py"
Task: "Implement progress indicators in src/neuroconv_client/cli/progress.py"
```

### Phase 3.7 Testing Utilities (Parallel: 3 tasks)
```bash
# Launch T033-T035 together:
Task: "Implement MockMCPServer in src/neuroconv_client/testing/mock_server.py"
Task: "Implement test fixtures in tests/conftest.py"
Task: "Implement logging configuration in src/neuroconv_client/utils/logging.py"
```

### Phase 3.8 Unit Tests (Parallel: 5 tasks)
```bash
# Launch T036-T040 together:
Task: "Unit tests for MCPConfig in tests/unit/test_config.py"
Task: "Unit tests for ConversionRequest/Response in tests/unit/test_models.py"
Task: "Unit tests for protocol handler in tests/unit/mcp/test_protocol.py"
Task: "Unit tests for retry logic in tests/unit/utils/test_retry.py"
Task: "Unit tests for CLI formatters in tests/unit/cli/test_formatting.py"
```

---

## Task Summary

### By Category
- **Setup**: 5 tasks (T001-T005)
- **Contract Tests**: 4 tasks (T006-T009)
- **Integration Tests**: 6 tasks (T010-T015)
- **Models**: 4 tasks (T016-T019)
- **MCP Protocol**: 4 tasks (T020-T023)
- **Client**: 3 tasks (T024-T026)
- **CLI**: 6 tasks (T027-T032)
- **Testing Utilities**: 3 tasks (T033-T035)
- **Unit Tests**: 5 tasks (T036-T040)
- **Documentation**: 2 tasks (T041-T042)

### Execution Stats
- **Total Tasks**: 42
- **Parallel Tasks**: 25 marked [P]
- **Sequential Tasks**: 17
- **Test Tasks**: 15 (contract + integration + unit)
- **Implementation Tasks**: 22 (models + protocol + client + CLI)
- **Polish Tasks**: 5 (testing utilities + docs + validation)

### Key Milestones
1. **After T005**: Project setup complete, ready for TDD
2. **After T015**: All tests written and failing (TDD gate)
3. **After T019**: Core models implemented
4. **After T026**: Client library functional
5. **After T032**: CLI tool complete
6. **After T040**: Unit tests complete
7. **After T042**: Feature complete, validated, documented

---

## Notes

### TDD Workflow
1. Write tests first (T006-T015) - **MUST FAIL**
2. Verify tests fail (pytest should show failures)
3. Implement models (T016-T019) - some tests may pass
4. Implement protocol + client (T020-T026) - more tests pass
5. Implement CLI (T027-T032) - all integration tests pass
6. Add unit tests (T036-T040) - increase coverage
7. Validate (T042) - ensure ≥85% coverage

### Parallel Task Guidelines
- [P] tasks operate on **different files**
- No [P] if tasks modify same file
- Contract tests are independent [P]
- Integration tests are independent [P]
- Model files are independent [P]
- CLI command files are independent [P]
- Unit test files are independent [P]

### Commit Strategy
- Commit after each task completion
- Commit message format: "feat(007): [task description]"
- Example: "feat(007): Add contract test for convert operation (T006)"
- Run tests before each commit
- Ensure no broken tests in commits

### Cross-Platform Considerations
- Use `pathlib.Path` for all file paths (T016-T017)
- Use `subprocess.Popen` with list args, no shell=True (T021)
- Test on Windows, macOS, Linux in CI (T005)
- Handle line endings in stdio communication (T021)

### Performance Targets (validate in T042)
- Client initialization: <50ms
- Connection establishment: <200ms
- Sync API overhead: <100ms
- Async API first response: <500ms
- Streaming chunk delivery: <50ms
- Memory per connection: <10MB

---

## Validation Checklist
*GATE: Checked before marking feature complete*

- [ ] All 4 contracts have corresponding tests (T006-T009)
- [ ] All 10 entities have model implementations (T016-T019)
- [ ] All tests written before implementation (T006-T015 before T016+)
- [ ] All 25 [P] tasks are truly independent (different files)
- [ ] Each task specifies exact file path in description
- [ ] No task modifies same file as another [P] task
- [ ] Test coverage ≥85% (validated in T042)
- [ ] All integration tests pass with MockMCPServer
- [ ] Type checking passes with mypy --strict
- [ ] Linting passes with ruff check
- [ ] Cross-platform tests pass on Windows, macOS, Linux
- [ ] Python 3.8-3.12 compatibility validated
- [ ] All quickstart examples executable (from quickstart.md)
- [ ] Documentation complete (API docs, CLI reference)

---

**Status**: Tasks generated - Ready for execution (42 tasks total, 25 parallel)
**Next Step**: Execute tasks T001-T042 in order, respecting dependencies
**Estimated Effort**: 40-50 hours (with parallelization: 25-30 hours)
