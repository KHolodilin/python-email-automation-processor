"""Tests for IMAP commands."""

import unittest
from unittest.mock import MagicMock, patch

from email_processor.cli.commands.imap import _display_results, _display_results_rich, run_processor
from email_processor.cli.ui import CLIUI
from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult


class TestDisplayResults(unittest.TestCase):
    """Tests for display results functions."""

    def setUp(self):
        """Setup test fixtures."""
        self.ui = MagicMock(spec=CLIUI)
        self.ui.has_rich = False
        self.ui.console = None

    def test_display_results_without_rich(self):
        """Test _display_results without rich console."""
        result = ProcessingResult(processed=5, skipped=3, errors=1, blocked=2)
        _display_results(result, self.ui)
        self.ui.info.assert_called_once()
        call_args = str(self.ui.info.call_args)
        self.assertIn("Processed: 5", call_args)
        self.assertIn("Skipped: 3", call_args)
        self.assertIn("Errors: 1", call_args)
        self.assertIn("Blocked: 2", call_args)

    @patch("email_processor.cli.commands.imap._display_results_rich")
    def test_display_results_with_rich(self, mock_rich):
        """Test _display_results with rich console."""
        self.ui.has_rich = True
        self.ui.console = MagicMock()
        result = ProcessingResult(processed=5, skipped=3, errors=1)
        _display_results(result, self.ui)
        mock_rich.assert_called_once_with(result, self.ui.console)

    def _mock_rich_table(self):
        """Helper to create mock rich.table module."""
        mock_table_class = MagicMock()
        mock_table_instance = MagicMock()
        mock_table_class.return_value = mock_table_instance

        # Create mock module
        mock_rich_table = MagicMock()
        mock_rich_table.Table = mock_table_class

        return mock_table_class, mock_table_instance, mock_rich_table

    @patch("builtins.__import__")
    def test_display_results_rich_basic(self, mock_import):
        """Test _display_results_rich with basic results."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        result = ProcessingResult(processed=5, skipped=3, errors=0, blocked=1)
        _display_results_rich(result, console)

        mock_table_class.assert_called()
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_errors(self, mock_import):
        """Test _display_results_rich with errors."""
        _mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        result = ProcessingResult(processed=5, skipped=3, errors=2, blocked=1)
        _display_results_rich(result, console)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_file_stats(self, mock_import):
        """Test _display_results_rich with file statistics."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        result = ProcessingResult(
            processed=5,
            skipped=3,
            errors=0,
            file_stats={".pdf": 3, ".txt": 2, ".doc": 1},
        )
        _display_results_rich(result, console)
        self.assertGreater(mock_table_class.call_count, 0)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_metrics_short_time(self, mock_import):
        """Test _display_results_rich with metrics showing milliseconds."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(total_time=0.5)  # Less than 1 second
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_metrics_seconds(self, mock_import):
        """Test _display_results_rich with metrics showing seconds."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(total_time=45.5)  # Less than 60 seconds
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_metrics_long_time(self, mock_import):
        """Test _display_results_rich with metrics showing minutes."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(total_time=125.5)  # More than 60 seconds
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_per_email_time(self, mock_import):
        """Test _display_results_rich with per email time metrics."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(total_time=10.0, per_email_time=[0.5, 0.3, 0.2, 0.4, 0.6])
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_imap_operations(self, mock_import):
        """Test _display_results_rich with IMAP operations metrics."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(
            total_time=10.0, imap_operations=10, imap_operation_times=[0.1, 0.2, 0.15]
        )
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_downloaded_size_kb(self, mock_import):
        """Test _display_results_rich with downloaded size in KB."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(total_time=10.0, total_downloaded_size=51200)  # 50 KB
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_downloaded_size_mb(self, mock_import):
        """Test _display_results_rich with downloaded size in MB."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(total_time=10.0, total_downloaded_size=2 * 1024 * 1024)  # 2 MB
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_with_memory_usage(self, mock_import):
        """Test _display_results_rich with memory usage metrics."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        metrics = ProcessingMetrics(
            total_time=10.0,
            memory_current=50 * 1024 * 1024,  # 50 MB
            memory_peak=100 * 1024 * 1024,  # 100 MB
        )
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        self.assertEqual(mock_table_class.call_count, 2)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_without_metrics(self, mock_import):
        """Test _display_results_rich without metrics."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=None)
        _display_results_rich(result, console)
        # Should only create results table, not metrics table
        self.assertEqual(mock_table_class.call_count, 1)
        console.print.assert_called()

    @patch("builtins.__import__")
    def test_display_results_rich_metrics_without_total_time(self, mock_import):
        """Test _display_results_rich with metrics but no total_time."""
        mock_table_class, _mock_table_instance, mock_rich_table = self._mock_rich_table()
        mock_import.side_effect = lambda name, *args, **kwargs: (
            mock_rich_table if name == "rich.table" else __import__(name, *args, **kwargs)
        )

        console = MagicMock()
        # Create metrics without total_time - use object without total_time attribute
        metrics = MagicMock()
        metrics.total_time = None  # Set to None instead of deleting
        result = ProcessingResult(processed=5, skipped=3, errors=0, metrics=metrics)
        _display_results_rich(result, console)
        # Should only create results table, not metrics table (because total_time check fails)
        # Actually, the check is: hasattr(result.metrics, "total_time") and isinstance(result.metrics.total_time, (int, float))
        # So if total_time is None, it will fail the isinstance check and not create metrics table
        self.assertEqual(mock_table_class.call_count, 1)
        console.print.assert_called()

    def test_display_results_rich_without_rich_available(self):
        """Test _display_results_rich when rich is not available."""
        console = MagicMock()
        # Patch the import inside the function
        with patch("builtins.__import__", side_effect=ImportError("No module named 'rich'")):
            result = ProcessingResult(processed=5, skipped=3, errors=0)
            # Should not raise, just return
            _display_results_rich(result, console)
            # Should not print anything if import fails
            console.print.assert_not_called()


class TestRunProcessor(unittest.TestCase):
    """Tests for run_processor function."""

    def setUp(self):
        """Setup test fixtures."""
        self.ui = MagicMock(spec=CLIUI)
        self.ui.has_rich = False
        self.ui.console = None

    @patch("email_processor.cli.commands.imap.EmailProcessor")
    @patch("email_processor.cli.commands.imap._display_results")
    def test_run_processor_success(self, mock_display, mock_processor_class):
        """Test run_processor with successful processing."""
        mock_processor = MagicMock()
        mock_processor.process.return_value = ProcessingResult(processed=5, skipped=3, errors=0)
        mock_processor_class.return_value = mock_processor

        cfg = {"imap": {}, "processing": {}}
        result = run_processor(cfg, False, False, "config.yaml", self.ui)
        self.assertEqual(result, 0)
        mock_processor.process.assert_called_once()
        mock_display.assert_called_once()

    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_run_processor_keyboard_interrupt(self, mock_processor_class):
        """Test run_processor handles KeyboardInterrupt."""
        mock_processor = MagicMock()
        mock_processor.process.side_effect = KeyboardInterrupt()
        mock_processor_class.return_value = mock_processor

        cfg = {"imap": {}, "processing": {}}
        with patch("email_processor.cli.commands.imap.logging") as mock_logging:
            result = run_processor(cfg, False, False, "config.yaml", self.ui)
            self.assertEqual(result, 0)
            mock_logging.info.assert_called_once()

    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_run_processor_exception(self, mock_processor_class):
        """Test run_processor handles general exceptions."""
        mock_processor = MagicMock()
        mock_processor.process.side_effect = Exception("Fatal error")
        mock_processor_class.return_value = mock_processor

        cfg = {"imap": {}, "processing": {}}
        with patch("email_processor.cli.commands.imap.logging") as mock_logging:
            result = run_processor(cfg, False, False, "config.yaml", self.ui)
            self.assertEqual(result, 1)
            mock_logging.exception.assert_called_once()
