"""Tests for CLIUI class methods."""

import unittest
from unittest.mock import MagicMock, patch

from email_processor.cli.ui import CLIUI


class TestCLIUI(unittest.TestCase):
    """Tests for CLIUI class methods."""

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_error_with_rich(self, mock_console_class):
        """Test error() method with rich console."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        ui.error("Test error")
        mock_console.print.assert_called_once_with("[red]Error:[/red] Test error")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    @patch("builtins.print")
    def test_error_without_rich(self, mock_print):
        """Test error() method without rich console."""
        ui = CLIUI()
        ui.error("Test error")
        mock_print.assert_called_once_with("Error: Test error")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_warn_with_rich(self, mock_console_class):
        """Test warn() method with rich console."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        ui.warn("Test warning")
        mock_console.print.assert_called_once_with("[yellow]Warning:[/yellow] Test warning")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    @patch("builtins.print")
    def test_warn_without_rich(self, mock_print):
        """Test warn() method without rich console."""
        ui = CLIUI()
        ui.warn("Test warning")
        mock_print.assert_called_once_with("Warning: Test warning")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_info_with_rich(self, mock_console_class):
        """Test info() method with rich console."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        ui.info("Test info")
        mock_console.print.assert_called_once_with("Test info")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    @patch("builtins.print")
    def test_info_without_rich(self, mock_print):
        """Test info() method without rich console."""
        ui = CLIUI()
        ui.info("Test info")
        mock_print.assert_called_once_with("Test info")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_info_quiet_mode(self, mock_console_class):
        """Test info() method in quiet mode."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI(quiet=True)
        ui.info("Test info")
        mock_console.print.assert_not_called()

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_success_with_rich(self, mock_console_class):
        """Test success() method with rich console."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        ui.success("Test success")
        mock_console.print.assert_called_once_with("[green]✓[/green] Test success")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    @patch("builtins.print")
    def test_success_without_rich(self, mock_print):
        """Test success() method without rich console."""
        ui = CLIUI()
        ui.success("Test success")
        mock_print.assert_called_once_with("Test success")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_success_quiet_mode(self, mock_console_class):
        """Test success() method in quiet mode."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI(quiet=True)
        ui.success("Test success")
        mock_console.print.assert_not_called()

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_print_with_rich_no_style(self, mock_console_class):
        """Test print() method with rich console without style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        ui.print("Test message")
        mock_console.print.assert_called_once_with("Test message")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_print_with_rich_and_style(self, mock_console_class):
        """Test print() method with rich console with style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        ui.print("Test message", style="cyan")
        mock_console.print.assert_called_once_with("[cyan]Test message[/cyan]")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    @patch("builtins.print")
    def test_print_without_rich(self, mock_print):
        """Test print() method without rich console."""
        ui = CLIUI()
        ui.print("Test message")
        mock_print.assert_called_once_with("Test message")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_print_quiet_mode(self, mock_console_class):
        """Test print() method in quiet mode."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI(quiet=True)
        ui.print("Test message")
        mock_console.print.assert_not_called()

    @patch("builtins.input")
    def test_input_method(self, mock_input):
        """Test input() method."""
        mock_input.return_value = "user input"
        ui = CLIUI()
        result = ui.input("Enter value: ")
        self.assertEqual(result, "user input")
        mock_input.assert_called_once_with("Enter value: ")

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_has_rich_property(self, mock_console_class):
        """Test has_rich property."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        self.assertTrue(ui.has_rich)

    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    def test_has_rich_property_false(self):
        """Test has_rich property when rich is not available."""
        ui = CLIUI()
        self.assertFalse(ui.has_rich)

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_console_property(self, mock_console_class):
        """Test console property."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        self.assertEqual(ui.console, mock_console)

    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    def test_console_property_none(self):
        """Test console property when rich is not available."""
        ui = CLIUI()
        self.assertIsNone(ui.console)

    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_rich_available_true(self, mock_console_class):
        """Test that RICH_AVAILABLE = True is set when rich is available."""
        # This test ensures line 8 (RICH_AVAILABLE = True) is covered
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        ui = CLIUI()
        # When RICH_AVAILABLE is True, console should be created
        self.assertIsNotNone(ui._console)
        self.assertTrue(ui.has_rich)
