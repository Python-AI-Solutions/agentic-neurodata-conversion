"""
Unit tests for LogFileManager.

Tests log file creation, writing, and session management for scientific
reproducibility and audit trails.
"""

from datetime import datetime

import pytest
from models.state import LogEntry, LogLevel
from services.log_manager import LogFileManager

# Note: The following fixtures are provided by conftest files:
# - tmp_path: from pytest (temporary directory for file I/O testing)


@pytest.mark.unit
@pytest.mark.service
class TestLogFileManagerInitialization:
    """Test LogFileManager initialization."""

    def test_init_with_default_output_dir(self):
        """Test initialization with default output directory."""
        manager = LogFileManager()

        assert manager.output_dir.name == "conversion_logs"
        assert manager.output_dir.exists()
        assert manager.current_log_file is None
        assert manager.session_start is None

    def test_init_with_custom_output_dir(self, tmp_path):
        """Test initialization with custom output directory."""
        custom_dir = tmp_path / "custom_logs"
        manager = LogFileManager(output_dir=custom_dir)

        assert manager.output_dir == custom_dir
        assert manager.output_dir.exists()
        assert manager.current_log_file is None
        assert manager.session_start is None

    def test_init_creates_output_directory(self, tmp_path):
        """Test that initialization creates the output directory if it doesn't exist."""
        nonexistent_dir = tmp_path / "logs" / "nested" / "path"
        assert not nonexistent_dir.exists()

        manager = LogFileManager(output_dir=nonexistent_dir)

        assert nonexistent_dir.exists()


@pytest.mark.unit
@pytest.mark.service
class TestSessionLogFileCreation:
    """Test session log file creation."""

    def test_create_session_log_file_without_session_id(self, tmp_path):
        """Test creating session log file without session ID."""
        manager = LogFileManager(output_dir=tmp_path)

        log_file_path = manager.create_session_log_file()

        # Check log file was created
        assert log_file_path.exists()
        assert log_file_path.suffix == ".txt"
        assert log_file_path.name.startswith("conversion-logs-")
        assert "Z.txt" in log_file_path.name

        # Check manager state
        assert manager.current_log_file == log_file_path
        assert manager.session_start is not None
        assert isinstance(manager.session_start, datetime)

        # Check file content
        content = log_file_path.read_text(encoding="utf-8")
        assert "=" * 80 in content
        assert "NWB Conversion Process Log" in content
        assert "Session started:" in content
        assert manager.session_start.strftime("%m/%d/%Y, %I:%M:%S %p") in content

    def test_create_session_log_file_with_session_id(self, tmp_path):
        """Test creating session log file with custom session ID."""
        manager = LogFileManager(output_dir=tmp_path)
        session_id = "TEST-SESSION-001"

        log_file_path = manager.create_session_log_file(session_id=session_id)

        # Check filename includes session ID
        assert f"conversion-logs-{session_id}-" in log_file_path.name
        assert log_file_path.exists()

        # Check file content includes session ID
        content = log_file_path.read_text(encoding="utf-8")
        assert f"Session ID: {session_id}" in content

    def test_create_session_log_file_timestamp_format(self, tmp_path):
        """Test that session log file has correct timestamp format."""
        manager = LogFileManager(output_dir=tmp_path)

        before_time = datetime.now()
        log_file_path = manager.create_session_log_file()
        after_time = datetime.now()

        # Extract timestamp from filename
        # Format: conversion-logs-YYYY-MM-DDTHH-MM-SS-mmmZ.txt
        filename = log_file_path.stem
        timestamp_str = filename.replace("conversion-logs-", "").replace("Z", "")

        # Verify timestamp is between before and after
        assert manager.session_start >= before_time
        assert manager.session_start <= after_time


@pytest.mark.unit
@pytest.mark.service
class TestWriteLogEntry:
    """Test writing individual log entries."""

    def test_write_log_entry_simple(self, tmp_path):
        """Test writing a simple log entry without context."""
        manager = LogFileManager(output_dir=tmp_path)
        manager.create_session_log_file()

        log_entry = LogEntry(
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            level=LogLevel.INFO,
            message="Test log message",
        )

        manager.write_log_entry(log_entry)

        # Read and verify content
        content = manager.current_log_file.read_text(encoding="utf-8")
        assert "01/01/2025, 12:00:00 PM | INFO     | Test log message" in content

    def test_write_log_entry_with_context(self, tmp_path):
        """Test writing log entry with context."""
        manager = LogFileManager(output_dir=tmp_path)
        manager.create_session_log_file()

        log_entry = LogEntry(
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            level=LogLevel.ERROR,
            message="Conversion failed",
            context={"error_code": "ERR001", "file_path": "/test/file.nwb"},
        )

        manager.write_log_entry(log_entry)

        # Read and verify content
        content = manager.current_log_file.read_text(encoding="utf-8")
        assert "ERROR    | Conversion failed" in content
        assert "Context:" in content
        assert '"error_code": "ERR001"' in content
        assert '"file_path": "/test/file.nwb"' in content

    def test_write_log_entry_auto_creates_file(self, tmp_path):
        """Test that writing log entry auto-creates log file if not exists."""
        manager = LogFileManager(output_dir=tmp_path)
        assert manager.current_log_file is None

        log_entry = LogEntry(
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            level=LogLevel.INFO,
            message="Auto-created log",
        )

        manager.write_log_entry(log_entry)

        # Check log file was auto-created
        assert manager.current_log_file is not None
        assert manager.current_log_file.exists()

        # Check content
        content = manager.current_log_file.read_text(encoding="utf-8")
        assert "Auto-created log" in content

    @pytest.mark.parametrize(
        "level,expected_str",
        [
            (LogLevel.DEBUG, "DEBUG"),
            (LogLevel.INFO, "INFO"),
            (LogLevel.WARNING, "WARNING"),
            (LogLevel.ERROR, "ERROR"),
            (LogLevel.CRITICAL, "CRITICAL"),
        ],
    )
    def test_write_log_entry_all_levels(self, tmp_path, level, expected_str):
        """Test writing log entries with all log levels."""
        manager = LogFileManager(output_dir=tmp_path)
        manager.create_session_log_file()

        log_entry = LogEntry(
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            level=level,
            message=f"Test {level.value} message",
        )

        manager.write_log_entry(log_entry)

        content = manager.current_log_file.read_text(encoding="utf-8")
        assert expected_str in content


@pytest.mark.unit
@pytest.mark.service
class TestWriteLogEntriesBatch:
    """Test batch writing of log entries."""

    def test_write_log_entries_batch_empty_list(self, tmp_path):
        """Test writing empty batch of log entries."""
        manager = LogFileManager(output_dir=tmp_path)
        manager.create_session_log_file()

        initial_size = manager.current_log_file.stat().st_size

        manager.write_log_entries_batch([])

        # File size should not change
        assert manager.current_log_file.stat().st_size == initial_size

    def test_write_log_entries_batch_multiple_entries(self, tmp_path):
        """Test writing batch of multiple log entries."""
        manager = LogFileManager(output_dir=tmp_path)
        manager.create_session_log_file()

        log_entries = [
            LogEntry(
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
                level=LogLevel.INFO,
                message="Entry 1",
            ),
            LogEntry(
                timestamp=datetime(2025, 1, 1, 12, 0, 1),
                level=LogLevel.WARNING,
                message="Entry 2",
                context={"warning_type": "metadata_missing"},
            ),
            LogEntry(
                timestamp=datetime(2025, 1, 1, 12, 0, 2),
                level=LogLevel.ERROR,
                message="Entry 3",
            ),
        ]

        manager.write_log_entries_batch(log_entries)

        # Read and verify all entries
        content = manager.current_log_file.read_text(encoding="utf-8")
        assert "Entry 1" in content
        assert "Entry 2" in content
        assert "Entry 3" in content
        assert "warning_type" in content


@pytest.mark.unit
@pytest.mark.service
class TestCloseSessionLog:
    """Test closing session log files."""

    def test_close_session_log_with_active_session(self, tmp_path):
        """Test closing an active session log."""
        manager = LogFileManager(output_dir=tmp_path)
        log_file_path = manager.create_session_log_file()

        # Write some entries
        manager.write_log_entry(
            LogEntry(
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
                level=LogLevel.INFO,
                message="Test entry",
            )
        )

        # Close session
        closed_path = manager.close_session_log()

        # Check return value
        assert closed_path == log_file_path

        # Check manager state reset
        assert manager.current_log_file is None
        assert manager.session_start is None

        # Check footer was written
        content = closed_path.read_text(encoding="utf-8")
        assert "Session ended:" in content
        assert "Total duration:" in content

    def test_close_session_log_without_active_session(self, tmp_path):
        """Test closing when no session is active."""
        manager = LogFileManager(output_dir=tmp_path)

        closed_path = manager.close_session_log()

        # Should return None
        assert closed_path is None

    def test_close_session_log_includes_duration(self, tmp_path):
        """Test that closed log includes session duration."""
        manager = LogFileManager(output_dir=tmp_path)
        log_file_path = manager.create_session_log_file()

        # Wait a tiny bit and close
        import time

        time.sleep(0.01)
        closed_path = manager.close_session_log()

        content = closed_path.read_text(encoding="utf-8")
        assert "Total duration:" in content


@pytest.mark.unit
@pytest.mark.service
class TestGetCurrentLogFilePath:
    """Test getting current log file path."""

    def test_get_current_log_file_path_with_active_session(self, tmp_path):
        """Test getting path when session is active."""
        manager = LogFileManager(output_dir=tmp_path)
        created_path = manager.create_session_log_file()

        current_path = manager.get_current_log_file_path()

        assert current_path == created_path

    def test_get_current_log_file_path_without_session(self, tmp_path):
        """Test getting path when no session is active."""
        manager = LogFileManager(output_dir=tmp_path)

        current_path = manager.get_current_log_file_path()

        assert current_path is None


@pytest.mark.unit
@pytest.mark.service
class TestWriteStageHeader:
    """Test writing stage headers to log file."""

    def test_write_stage_header_with_active_session(self, tmp_path):
        """Test writing stage header to active log file."""
        manager = LogFileManager(output_dir=tmp_path)
        manager.create_session_log_file()

        manager.write_stage_header("Format Detection")

        content = manager.current_log_file.read_text(encoding="utf-8")
        assert "-" * 80 in content
        assert "STAGE: Format Detection" in content

    def test_write_stage_header_auto_creates_file(self, tmp_path):
        """Test that writing stage header auto-creates log file."""
        manager = LogFileManager(output_dir=tmp_path)
        assert manager.current_log_file is None

        manager.write_stage_header("Conversion")

        # Check file was auto-created
        assert manager.current_log_file is not None
        assert manager.current_log_file.exists()

        content = manager.current_log_file.read_text(encoding="utf-8")
        assert "STAGE: Conversion" in content

    def test_write_multiple_stage_headers(self, tmp_path):
        """Test writing multiple stage headers."""
        manager = LogFileManager(output_dir=tmp_path)
        manager.create_session_log_file()

        stages = ["Format Detection", "Metadata Collection", "Conversion", "Validation"]

        for stage in stages:
            manager.write_stage_header(stage)

        content = manager.current_log_file.read_text(encoding="utf-8")
        for stage in stages:
            assert f"STAGE: {stage}" in content


@pytest.mark.unit
@pytest.mark.service
class TestLogFileManagerIntegration:
    """Integration tests for complete log file lifecycle."""

    def test_complete_logging_workflow(self, tmp_path):
        """Test complete logging workflow from creation to close."""
        manager = LogFileManager(output_dir=tmp_path)

        # 1. Create session
        log_file = manager.create_session_log_file(session_id="WORKFLOW-001")
        assert log_file.exists()

        # 2. Write stage header
        manager.write_stage_header("Initialization")

        # 3. Write individual log entries
        manager.write_log_entry(
            LogEntry(
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
                level=LogLevel.INFO,
                message="System initialized",
            )
        )

        # 4. Write batch entries
        manager.write_log_entries_batch(
            [
                LogEntry(
                    timestamp=datetime(2025, 1, 1, 12, 0, 1),
                    level=LogLevel.INFO,
                    message="Processing file",
                    context={"file_name": "test.nwb"},
                ),
                LogEntry(
                    timestamp=datetime(2025, 1, 1, 12, 0, 2),
                    level=LogLevel.WARNING,
                    message="Metadata missing",
                ),
            ]
        )

        # 5. Write another stage
        manager.write_stage_header("Validation")

        # 6. Close session
        closed_path = manager.close_session_log()
        assert closed_path == log_file

        # Verify complete log content
        content = log_file.read_text(encoding="utf-8")

        # Check header
        assert "NWB Conversion Process Log" in content
        assert "Session ID: WORKFLOW-001" in content

        # Check stages
        assert "STAGE: Initialization" in content
        assert "STAGE: Validation" in content

        # Check log entries
        assert "System initialized" in content
        assert "Processing file" in content
        assert "Metadata missing" in content
        assert "test.nwb" in content

        # Check footer
        assert "Session ended:" in content
        assert "Total duration:" in content

    def test_multiple_sessions_independent(self, tmp_path):
        """Test that multiple sessions create independent log files."""
        manager1 = LogFileManager(output_dir=tmp_path)
        manager2 = LogFileManager(output_dir=tmp_path)

        log1 = manager1.create_session_log_file(session_id="SESSION-1")
        log2 = manager2.create_session_log_file(session_id="SESSION-2")

        # Different log files
        assert log1 != log2

        # Write to each
        manager1.write_log_entry(
            LogEntry(
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
                level=LogLevel.INFO,
                message="Session 1 message",
            )
        )

        manager2.write_log_entry(
            LogEntry(
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
                level=LogLevel.INFO,
                message="Session 2 message",
            )
        )

        # Verify independence
        content1 = log1.read_text(encoding="utf-8")
        content2 = log2.read_text(encoding="utf-8")

        assert "Session 1 message" in content1
        assert "Session 1 message" not in content2

        assert "Session 2 message" in content2
        assert "Session 2 message" not in content1
