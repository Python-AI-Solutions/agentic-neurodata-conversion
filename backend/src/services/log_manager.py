"""
Log file manager for conversion process.

This module handles persistent logging to disk for scientific transparency
and traceability. Each conversion session generates a timestamped log file
containing detailed process information.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from models.state import LogEntry, LogLevel


class LogFileManager:
    """
    Manages persistent log file creation and writing for conversion sessions.

    Each conversion session gets a unique timestamped log file that captures
    all process details for scientific reproducibility and audit trails.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the log file manager.

        Args:
            output_dir: Directory to store log files. Defaults to backend/src/outputs/conversion_logs/
        """
        if output_dir is None:
            # Default to backend/src/outputs/conversion_logs/
            base_dir = Path(__file__).parent.parent / "outputs" / "conversion_logs"
        else:
            base_dir = Path(output_dir)

        self.output_dir = base_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file: Optional[Path] = None
        self.session_start: Optional[datetime] = None

    def create_session_log_file(self, session_id: Optional[str] = None) -> Path:
        """
        Create a new log file for a conversion session.

        Args:
            session_id: Optional session identifier. If not provided, uses timestamp.

        Returns:
            Path to the created log file
        """
        self.session_start = datetime.now()

        # Generate filename with timestamp
        timestamp_str = self.session_start.strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"

        if session_id:
            filename = f"conversion-logs-{session_id}-{timestamp_str}.txt"
        else:
            filename = f"conversion-logs-{timestamp_str}.txt"

        self.current_log_file = self.output_dir / filename

        # Write header
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            f.write(f"=" * 80 + "\n")
            f.write(f"NWB Conversion Process Log\n")
            f.write(f"Session started: {self.session_start.strftime('%m/%d/%Y, %I:%M:%S %p')}\n")
            if session_id:
                f.write(f"Session ID: {session_id}\n")
            f.write(f"=" * 80 + "\n\n")

        return self.current_log_file

    def write_log_entry(self, log_entry: LogEntry) -> None:
        """
        Write a log entry to the current log file.

        Args:
            log_entry: LogEntry to write
        """
        if self.current_log_file is None:
            # Auto-create log file if not exists
            self.create_session_log_file()

        with open(self.current_log_file, 'a', encoding='utf-8') as f:
            # Format timestamp
            timestamp_str = log_entry.timestamp.strftime('%m/%d/%Y, %I:%M:%S %p')

            # Format log level
            level_str = log_entry.level.value.upper()
            level_padded = f"{level_str:<8}"  # Left-align, 8 chars wide

            # Write log line
            f.write(f"{timestamp_str} | {level_padded} | {log_entry.message}\n")

            # Write context if present
            if log_entry.context:
                # Pretty-print context JSON with proper indentation
                context_json = json.dumps(log_entry.context, indent=2, default=str)
                # Indent each line of context
                indented_context = "\n".join(
                    "                         " + line  # Align with message
                    for line in context_json.split("\n")
                )
                f.write(f"                         Context: \n{indented_context}\n")

            f.write("\n")  # Blank line between entries

    def write_log_entries_batch(self, log_entries: list[LogEntry]) -> None:
        """
        Write multiple log entries in batch.

        Args:
            log_entries: List of LogEntry objects to write
        """
        for log_entry in log_entries:
            self.write_log_entry(log_entry)

    def close_session_log(self) -> Optional[Path]:
        """
        Close the current session log file with a footer.

        Returns:
            Path to the closed log file, or None if no log file was open
        """
        if self.current_log_file is None:
            return None

        session_end = datetime.now()
        duration = session_end - self.session_start if self.session_start else None

        with open(self.current_log_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Session ended: {session_end.strftime('%m/%d/%Y, %I:%M:%S %p')}\n")
            if duration:
                f.write(f"Total duration: {duration}\n")
            f.write("=" * 80 + "\n")

        log_file_path = self.current_log_file
        self.current_log_file = None
        self.session_start = None

        return log_file_path

    def get_current_log_file_path(self) -> Optional[Path]:
        """
        Get the path to the current log file.

        Returns:
            Path to current log file, or None if no session active
        """
        return self.current_log_file

    def write_stage_header(self, stage_name: str) -> None:
        """
        Write a visual stage separator in the log file.

        Args:
            stage_name: Name of the stage
        """
        if self.current_log_file is None:
            self.create_session_log_file()

        with open(self.current_log_file, 'a', encoding='utf-8') as f:
            f.write("-" * 80 + "\n")
            f.write(f"STAGE: {stage_name}\n")
            f.write("-" * 80 + "\n\n")
