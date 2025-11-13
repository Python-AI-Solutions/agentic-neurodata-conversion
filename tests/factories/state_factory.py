"""
Factory for generating GlobalState instances.

Provides programmatic generation of GlobalState objects in various
states for testing different workflow stages.
"""

from pathlib import Path

from agentic_neurodata_conversion.models import ConversionStatus, GlobalState

from .metadata_factory import MetadataFactory
from .validation_factory import ValidationFactory


class StateFactory:
    """Factory for generating GlobalState instances."""

    @staticmethod
    def create_initial_state() -> GlobalState:
        """Create a fresh GlobalState (just initialized)."""
        return GlobalState()

    @staticmethod
    def create_idle_state() -> GlobalState:
        """Create GlobalState in IDLE status."""
        state = GlobalState()
        state.status = ConversionStatus.IDLE
        return state

    @staticmethod
    def create_uploaded_state(input_path: Path | None = None) -> GlobalState:
        """Create GlobalState after file upload."""
        state = GlobalState()
        state.status = ConversionStatus.FORMAT_DETECTED
        state.input_path = str(input_path) if input_path else "/test/input.bin"
        state.detected_format = "SpikeGLX"
        return state

    @staticmethod
    def create_metadata_collection_state() -> GlobalState:
        """Create GlobalState during metadata collection."""
        state = GlobalState()
        state.status = ConversionStatus.AWAITING_USER_INPUT
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_partial_metadata()
        return state

    @staticmethod
    def create_converting_state() -> GlobalState:
        """Create GlobalState during conversion."""
        state = GlobalState()
        state.status = ConversionStatus.CONVERTING
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_complete_metadata()
        state.input_path = "/test/input.bin"
        state.output_path = "/test/output.nwb"
        return state

    @staticmethod
    def create_validating_state() -> GlobalState:
        """Create GlobalState during validation."""
        state = GlobalState()
        state.status = ConversionStatus.VALIDATING
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_complete_metadata()
        state.input_path = "/test/input.bin"
        state.output_path = "/test/output.nwb"
        return state

    @staticmethod
    def create_awaiting_approval_state(validation_result: dict | None = None) -> GlobalState:
        """Create GlobalState awaiting user approval for retry."""
        state = GlobalState()
        state.status = ConversionStatus.AWAITING_APPROVAL
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_complete_metadata()
        state.input_path = "/test/input.bin"
        state.output_path = "/test/output.nwb"

        if validation_result is None:
            validation_result = ValidationFactory.create_failed_result()

        state.validation_result = validation_result
        return state

    @staticmethod
    def create_completed_state(validation_passed: bool = True) -> GlobalState:
        """Create GlobalState after successful completion."""
        state = GlobalState()
        state.status = ConversionStatus.COMPLETE
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_complete_metadata()
        state.input_path = "/test/input.bin"
        state.output_path = "/test/output.nwb"

        if validation_passed:
            state.validation_result = ValidationFactory.create_passed_result()
        else:
            state.validation_result = ValidationFactory.create_passed_with_warnings()

        return state

    @staticmethod
    def create_failed_state(error_message: str = "Conversion failed") -> GlobalState:
        """Create GlobalState after failure."""
        state = GlobalState()
        state.status = ConversionStatus.FAILED
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_complete_metadata()
        state.input_path = "/test/input.bin"
        state.error_message = error_message
        return state

    @staticmethod
    def create_retry_state(retry_count: int) -> GlobalState:
        """Create GlobalState during a retry attempt.

        Args:
            retry_count: Which retry attempt (1, 2, 3, etc.)

        Returns:
            GlobalState configured for retry scenario
        """
        state = GlobalState()
        state.status = ConversionStatus.CONVERTING
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_complete_metadata()
        state.input_path = "/test/input.bin"
        state.output_path = "/test/output.nwb"
        state.retry_count = retry_count

        # Previous validation result (from last attempt)
        state.validation_result = ValidationFactory.create_result_for_retry_attempt(retry_count - 1)

        return state

    @staticmethod
    def create_state_with_logs(num_logs: int = 5) -> GlobalState:
        """Create GlobalState with log history.

        Args:
            num_logs: Number of log entries to add

        Returns:
            GlobalState with populated log history
        """
        state = GlobalState()

        for i in range(num_logs):
            state.add_log(level="INFO", message=f"Log entry {i + 1}", agent="test_agent")

        return state

    @staticmethod
    def create_state_for_websocket_test() -> GlobalState:
        """Create GlobalState configured for WebSocket testing."""
        state = GlobalState()
        state.status = ConversionStatus.CONVERTING
        state.detected_format = "SpikeGLX"
        state.metadata = MetadataFactory.create_complete_metadata()
        state.input_path = "/test/input.bin"
        state.output_path = "/test/output.nwb"

        # Add logs for various stages
        state.add_log("INFO", "File uploaded", "api")
        state.add_log("INFO", "Format detected: SpikeGLX", "conversion")
        state.add_log("INFO", "Metadata collected", "conversation")
        state.add_log("INFO", "Conversion started", "conversion")

        return state

    @staticmethod
    def create_state_with_conversation_history() -> GlobalState:
        """Create GlobalState with conversation history."""
        state = GlobalState()
        state.status = ConversionStatus.AWAITING_USER_INPUT

        # Add conversation messages
        state.add_conversation_message("user", "I need to convert some data")
        state.add_conversation_message("assistant", "What format is your data?")
        state.add_conversation_message("user", "It's SpikeGLX")
        state.add_conversation_message("assistant", "Great! Let me collect metadata.")

        return state

    @staticmethod
    def create_custom_state(
        status: ConversionStatus, has_metadata: bool = False, has_validation_result: bool = False, retry_count: int = 0
    ) -> GlobalState:
        """Create a custom GlobalState.

        Args:
            status: ConversionStatus to set
            has_metadata: Whether to include metadata
            has_validation_result: Whether to include validation result
            retry_count: Number of retry attempts

        Returns:
            Customized GlobalState
        """
        state = GlobalState()
        state.status = status
        state.retry_count = retry_count

        if has_metadata:
            state.metadata = MetadataFactory.create_complete_metadata()

        if has_validation_result:
            state.validation_result = ValidationFactory.create_passed_result()

        return state
