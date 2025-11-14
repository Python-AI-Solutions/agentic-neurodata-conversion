"""
Unit tests for CLI (Command Line Interface).

Tests argument parsing, command execution, and server initialization.
"""

from unittest.mock import Mock, patch

import pytest

from agentic_neurodata_conversion.cli import main, start_server

# Note: CLI tests don't require async fixtures


@pytest.mark.unit
class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    def test_main_no_arguments_shows_help(self, capsys):
        """Test that running with no arguments shows help."""
        with patch("sys.argv", ["nwb-convert"]):
            main()

        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "AI-powered neurophysiology" in captured.out

    def test_main_version_argument(self, capsys):
        """Test --version argument."""
        with patch("sys.argv", ["nwb-convert", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with code 0
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "0.1.0" in captured.out

    def test_main_help_argument(self, capsys):
        """Test --help argument."""
        with patch("sys.argv", ["nwb-convert", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with code 0
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "AI-powered neurophysiology" in captured.out

    def test_main_server_subcommand_help(self, capsys):
        """Test server subcommand help."""
        with patch("sys.argv", ["nwb-convert", "server", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "server" in captured.out.lower()
        assert "--host" in captured.out
        assert "--port" in captured.out
        assert "--reload" in captured.out

    def test_main_convert_subcommand_help(self, capsys):
        """Test convert subcommand help."""
        with patch("sys.argv", ["nwb-convert", "convert", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "convert" in captured.out.lower()
        assert "input" in captured.out.lower()
        assert "output" in captured.out.lower()


@pytest.mark.unit
class TestServerCommand:
    """Test server command execution."""

    def test_server_command_default_args(self):
        """Test server command with default arguments."""
        # Create mock uvicorn module
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}), patch("sys.argv", ["nwb-convert", "server"]):
            main()

        # Check uvicorn.run was called with defaults
        mock_uvicorn.run.assert_called_once()
        call_kwargs = mock_uvicorn.run.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 8000
        assert call_kwargs["reload"] is False

    def test_server_command_custom_host_port(self):
        """Test server command with custom host and port."""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("sys.argv", ["nwb-convert", "server", "--host", "127.0.0.1", "--port", "3000"]):
                main()

        call_kwargs = mock_uvicorn.run.call_args[1]
        assert call_kwargs["host"] == "127.0.0.1"
        assert call_kwargs["port"] == 3000

    def test_server_command_with_reload(self):
        """Test server command with --reload flag."""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("sys.argv", ["nwb-convert", "server", "--reload"]):
                main()

        call_kwargs = mock_uvicorn.run.call_args[1]
        assert call_kwargs["reload"] is True

    def test_server_command_missing_uvicorn(self, capsys):
        """Test server command when uvicorn is not installed."""
        # Simulate ImportError when uvicorn is imported
        with patch.dict("sys.modules", {"uvicorn": None}), patch("sys.argv", ["nwb-convert", "server"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "uvicorn is not installed" in captured.out

    def test_server_command_prints_startup_info(self, capsys):
        """Test that server command prints startup information."""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("sys.argv", ["nwb-convert", "server", "--host", "localhost", "--port", "9000"]):
                main()

        captured = capsys.readouterr()
        assert "Starting Agentic Neurodata Conversion Server" in captured.out
        assert "Host: localhost" in captured.out
        assert "Port: 9000" in captured.out
        assert "http://localhost:9000" in captured.out


@pytest.mark.unit
class TestConvertCommand:
    """Test convert command execution."""

    def test_convert_command_not_implemented(self, capsys):
        """Test that convert command shows not implemented message."""
        with patch("sys.argv", ["nwb-convert", "convert", "input.bin", "output.nwb"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "not yet implemented" in captured.out.lower()
        assert "web interface" in captured.out.lower()

    def test_convert_command_with_format_option(self, capsys):
        """Test convert command with --format option."""
        with patch("sys.argv", ["nwb-convert", "convert", "input.bin", "output.nwb", "--format", "SpikeGLX"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "not yet implemented" in captured.out.lower()


@pytest.mark.unit
class TestStartServerFunction:
    """Test start_server function directly."""

    def test_start_server_basic(self, capsys):
        """Test start_server function with basic parameters."""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            start_server(host="0.0.0.0", port=8000, reload=False)

        # Check uvicorn.run was called correctly
        mock_uvicorn.run.assert_called_once()

        # Get both positional and keyword args
        call_args = mock_uvicorn.run.call_args[0]  # Positional args
        call_kwargs = mock_uvicorn.run.call_args[1]  # Keyword args

        # App is passed as a positional argument
        assert (
            len(call_args) == 0
            or "agentic_neurodata_conversion.api.main:app" in str(call_args)
            or "agentic_neurodata_conversion.api.main:app" in call_kwargs.get("app", "")
        )

        # Check keyword arguments
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 8000
        assert call_kwargs["reload"] is False

        # Check startup message was printed
        captured = capsys.readouterr()
        assert "Starting Agentic Neurodata Conversion Server" in captured.out

    def test_start_server_with_reload(self):
        """Test start_server with reload enabled."""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            start_server(host="127.0.0.1", port=3000, reload=True)

        call_kwargs = mock_uvicorn.run.call_args[1]
        assert call_kwargs["reload"] is True

    def test_start_server_uvicorn_not_installed(self, capsys):
        """Test start_server when uvicorn is not installed."""
        # Simulate ImportError
        with patch.dict("sys.modules", {"uvicorn": None}):
            with pytest.raises(SystemExit) as exc_info:
                start_server(host="0.0.0.0", port=8000, reload=False)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "uvicorn is not installed" in captured.out


@pytest.mark.unit
class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""

    def test_invalid_port_number(self):
        """Test that invalid port number is handled by argparse."""
        with patch("sys.argv", ["nwb-convert", "server", "--port", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # argparse should exit with code 2 for invalid arguments
            assert exc_info.value.code == 2

    def test_port_out_of_range(self):
        """Test that port number validation works."""
        # Note: argparse with type=int will allow any integer, but uvicorn/OS will validate range
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("sys.argv", ["nwb-convert", "server", "--port", "99999"]):
                main()

                # Should still call uvicorn (which will handle port validation)
                assert mock_uvicorn.run.called

    def test_empty_input_path_convert(self, capsys):
        """Test convert command with empty input path."""
        with patch("sys.argv", ["nwb-convert", "convert", "", "output.nwb"]), pytest.raises(SystemExit):
            main()

    def test_multiple_subcommands_not_allowed(self):
        """Test that multiple subcommands are not allowed."""
        with patch("sys.argv", ["nwb-convert", "server", "convert"]):
            # argparse will interpret "convert" as an unknown argument to server
            with pytest.raises(SystemExit):
                main()


@pytest.mark.unit
class TestCLIIntegration:
    """Integration tests for complete CLI workflows."""

    def test_typical_development_server_start(self, capsys):
        """Test typical development server startup."""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("sys.argv", ["nwb-convert", "server", "--host", "localhost", "--port", "8000", "--reload"]):
                main()

        # Verify complete flow
        assert mock_uvicorn.run.called
        call_kwargs = mock_uvicorn.run.call_args[1]
        assert call_kwargs["host"] == "localhost"
        assert call_kwargs["port"] == 8000
        assert call_kwargs["reload"] is True

        captured = capsys.readouterr()
        assert "localhost" in captured.out
        assert "8000" in captured.out
        assert "Reload: True" in captured.out

    def test_production_server_start(self, capsys):
        """Test production server startup (no reload)."""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("sys.argv", ["nwb-convert", "server", "--host", "0.0.0.0", "--port", "80"]):
                main()

        call_kwargs = mock_uvicorn.run.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 80
        assert call_kwargs["reload"] is False

        captured = capsys.readouterr()
        assert "Reload: False" in captured.out
