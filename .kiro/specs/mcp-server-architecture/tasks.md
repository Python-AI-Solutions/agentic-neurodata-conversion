# Implementation Plan

- [x] 1. Implement core service layer (transport-agnostic)
  - Create `agentic_neurodata_conversion/core/service.py` with business logic
    and data models
  - Implement `ConversionService` class with all conversion operations (analyze,
    convert, evaluate)
  - Add agent management and workflow orchestration without any transport
    dependencies
  - Create data models for requests, responses, and internal state (no MCP or
    FastAPI imports)
  - _Requirements: 1.1, 1.3, 3.1_

- [x] 2. Build agent management in core service layer
  - Implement `AgentManager` in core service for agent lifecycle management
  - Add agent execution coordination and error handling in transport-agnostic
    way
  - Create agent performance metrics and statistics tracking
  - Implement workflow orchestration for multi-step pipeline execution
  - _Requirements: 3.1, 3.2, 6.2, 6.3_

- [x] 3. Create tool registry and execution system in core layer
  - Implement tool registry system with metadata and execution tracking
  - Add tool categorization and discovery without transport-specific code
  - Create tool execution engine with timeout and error handling
  - Implement tool result processing and validation
  - _Requirements: 1.2, 6.2, 6.3_

- [ ] 4. Implement format detection and validation in core service
  - Create automatic format detection for neuroscience data types in core layer
  - Add dataset structure validation and error reporting
  - Implement format-specific interface selection logic
  - Create validation coordination for quality assessment systems
  - _Requirements: 4.1, 4.2, 4.3, 5.1_

- [ ] 5. Build session and state management in core service
  - Implement session tracking and pipeline state management
  - Add conversion progress monitoring and status reporting
  - Create session cleanup and cancellation handling
  - Implement comprehensive logging and error tracking
  - _Requirements: 1.3, 3.3, 6.1, 6.4_

- [x] 6. Create MCP adapter layer
  - Implement thin MCP adapter in
    `agentic_neurodata_conversion/mcp_server/mcp_adapter.py`
  - Map MCP methods (list_resources, read_resource, call_tool) to core service
    layer
  - Add MCP protocol compliance and message handling
  - Implement stdio transport for MCP communication
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 7. Implement MCP tool definitions and resource mappings
  - Create MCP tool definitions that call core service methods
  - Map conversion operations to MCP tool calls (dataset_analysis,
    conversion_orchestration, evaluate_nwb_file)
  - Implement MCP resource definitions for conversion artifacts
  - Add MCP-specific error handling and response formatting
  - _Requirements: 1.1, 1.2, 2.4_

- [x] 8. Build FastAPI HTTP adapter layer
  - Create FastAPI adapter in
    `agentic_neurodata_conversion/mcp_server/http_adapter.py`
  - Implement HTTP endpoints that call the same core service methods as MCP
    adapter
  - Add FastAPI-specific request/response models and validation
  - Create HTTP-specific error handling and middleware
  - _Requirements: 1.2, 1.4, 7.1_

- [x] 9. Implement HTTP endpoint routing and documentation
  - Create conversion endpoints (/analyze, /convert, /evaluate) calling core
    service
  - Add pipeline orchestration endpoint for full workflow
  - Implement monitoring and health check endpoints
  - Create OpenAPI documentation and endpoint descriptions
  - _Requirements: 1.1, 1.2, 6.1, 7.1_

- [ ] 10. Add configuration and customization support
  - Implement configuration management in core service layer
  - Add environment-based configuration for both MCP and HTTP adapters
  - Create agent parameter and timeout configuration
  - Implement deployment configuration for different environments
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 11. Create contract tests for core service layer
  - Implement comprehensive test suite that hits core service directly
  - Create test cases for all conversion operations and workflows
  - Add agent coordination and error handling tests
  - Implement performance and load testing for core service
  - _Requirements: 6.2, 6.3, 6.4_

- [x] 12. Build integration tests for adapter parity
  - Create integration tests that hit both MCP and FastAPI adapters
  - Verify that both adapters produce identical results from core service
  - Test error handling consistency between adapters
  - Validate protocol compliance for both MCP and HTTP interfaces
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 13. Implement adapter-specific features and optimizations
  - Add WebSocket support to FastAPI adapter for real-time updates
  - Implement local socket transport option for MCP adapter
  - Create adapter-specific middleware and error handling
  - Add transport-specific logging and monitoring
  - _Requirements: 2.1, 2.2, 6.1, 6.4_

- [ ] 14. Test and validate complete layered architecture
  - Verify clean separation between core service and adapter layers
  - Test that core service has no transport dependencies
  - Validate that both adapters provide equivalent functionality
  - Perform end-to-end testing of complete conversion workflows
  - _Requirements: 1.1, 1.2, 1.3, 1.4_
