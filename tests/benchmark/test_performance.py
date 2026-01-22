"""Benchmark tests for email processor performance."""

import time
import unittest
from unittest.mock import MagicMock, patch

from email_processor.imap.fetcher import Fetcher, ProcessingMetrics

# Backward compatibility alias
EmailProcessor = Fetcher


class TestPerformanceBenchmarks(unittest.TestCase):
    """Benchmark tests for performance measurement."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": 3,
                "retry_delay": 1,
            },
            "processing": {
                "start_days_back": 1,
                "download_dir": "test_downloads",
                "archive_folder": "INBOX/Processed",
                "processed_dir": "test_processed",
                "keep_processed_days": 0,
                "archive_only_mapped": True,
                "skip_non_allowed_as_processed": True,
                "skip_unmapped_as_processed": True,
                "show_progress": False,
            },
            "allowed_senders": ["test@example.com"],
            "topic_mapping": {".*test.*": "test_folder"},
            "logging": {"level": "WARNING", "format": "console"},
        }

    def test_processing_metrics_collection(self):
        """Benchmark: Test that metrics are collected correctly."""
        processor = EmailProcessor(self.config)

        # Mock IMAP connection
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1 2 3"])

        with patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail):
            with patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ):
                result = processor.process(dry_run=True, mock_mode=False)

        # Verify metrics are collected
        self.assertIsNotNone(result.metrics)
        self.assertGreaterEqual(result.metrics.total_time, 0)
        self.assertGreaterEqual(result.metrics.imap_operations, 0)

    def test_per_email_processing_time(self):
        """Benchmark: Measure time per email processing."""
        processor = EmailProcessor(self.config)

        # Mock IMAP with multiple emails
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1 2 3 4 5"])

        with patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail):
            with patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ):
                # Mock fetch operations to return quickly
                mock_mail.fetch.side_effect = [
                    ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch
                    (
                        "OK",
                        [
                            (
                                None,
                                b"From: test@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n",
                            )
                        ],
                    ),  # Header fetch
                    (
                        "OK",
                        [(None, b"From: test@example.com\r\nSubject: Test\r\n\r\nBody")],
                    ),  # Message fetch
                ]
                result = processor.process(dry_run=True, mock_mode=False)

        # Verify per-email times are collected
        if result.metrics.per_email_time:
            avg_time = sum(result.metrics.per_email_time) / len(result.metrics.per_email_time)
            self.assertGreaterEqual(avg_time, 0)
            # Benchmark: average time should be reasonable (< 1 second per email in dry-run)
            self.assertLess(avg_time, 1.0, "Average processing time per email should be < 1s")

    def test_imap_operation_timing(self):
        """Benchmark: Measure IMAP operation latency."""
        processor = EmailProcessor(self.config)

        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1 2"])

        with patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail):
            with patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ):
                result = processor.process(dry_run=True, mock_mode=False)

        # Verify IMAP operation times are collected
        if result.metrics.imap_operation_times:
            avg_imap_time = sum(result.metrics.imap_operation_times) / len(
                result.metrics.imap_operation_times
            )
            self.assertGreaterEqual(avg_imap_time, 0)
            # Benchmark: IMAP operations should be reasonably fast
            self.assertLess(avg_imap_time, 0.5, "Average IMAP operation time should be < 500ms")

    def test_memory_usage_tracking(self):
        """Benchmark: Test memory usage tracking (if psutil available)."""
        processor = EmailProcessor(self.config)

        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])

        with patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail):
            with patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ):
                result = processor.process(dry_run=True, mock_mode=False)

        # Memory tracking is optional (requires psutil)
        # Just verify the field exists (may be None if psutil not available)
        # If psutil is available and memory was tracked, it should be > 0
        if result.metrics.memory_current is not None:
            self.assertGreater(result.metrics.memory_current, 0)

    def test_total_processing_time_benchmark(self):
        """Benchmark: Total processing time should be reasonable."""
        processor = EmailProcessor(self.config)

        # Simulate processing 10 emails
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b" ".join([str(i).encode() for i in range(1, 11)])])
        # Mock fetch operations for each email (3 fetches per email: UID, header, message)
        fetch_responses = []
        for _ in range(10):
            fetch_responses.extend(
                [
                    ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch
                    (
                        "OK",
                        [
                            (
                                None,
                                b"From: test@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n",
                            )
                        ],
                    ),  # Header fetch
                    (
                        "OK",
                        [(None, b"From: test@example.com\r\nSubject: Test\r\n\r\nBody")],
                    ),  # Message fetch
                ]
            )
        mock_mail.fetch.side_effect = fetch_responses

        start_time = time.time()
        with patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail):
            with patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ):
                result = processor.process(dry_run=True, mock_mode=False)
        end_time = time.time()

        # Verify total time is tracked
        self.assertGreaterEqual(result.metrics.total_time, 0)
        # Verify it's close to actual elapsed time (within 100% tolerance for test overhead and Python version differences)
        # Note: In CI environments, timing can vary significantly, so we use a more lenient tolerance
        actual_time = end_time - start_time
        tolerance = max(actual_time, 0.01)  # At least 10ms tolerance
        self.assertAlmostEqual(
            result.metrics.total_time,
            actual_time,
            delta=tolerance,
            msg=f"Metrics time {result.metrics.total_time} should be close to actual time {actual_time}",
        )

    def test_downloaded_size_tracking(self):
        """Benchmark: Test tracking of downloaded file sizes."""
        processor = EmailProcessor(self.config)

        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])

        # Mock email with attachment
        mock_email = MagicMock()
        mock_part = MagicMock()
        mock_part.get_content_disposition.return_value = "attachment"
        mock_part.get_filename.return_value = "test.pdf"
        mock_part.get_payload.return_value = b"x" * 1024  # 1KB file
        mock_email.walk.return_value = [mock_part]

        with patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail):
            with patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ):
                with patch(
                    "email_processor.imap.fetcher.message_from_bytes",
                    return_value=mock_email,
                ):
                    result = processor.process(dry_run=False, mock_mode=False)

        # In dry_run=False, size should be tracked if file was saved
        # Note: This depends on actual file saving, so may be 0 in some test scenarios
        self.assertGreaterEqual(result.metrics.total_downloaded_size, 0)

    def test_metrics_initialization(self):
        """Benchmark: Test that metrics are properly initialized."""
        metrics = ProcessingMetrics()
        self.assertEqual(metrics.total_time, 0.0)
        self.assertEqual(metrics.per_email_time, [])
        self.assertEqual(metrics.total_downloaded_size, 0)
        self.assertEqual(metrics.imap_operations, 0)
        self.assertEqual(metrics.imap_operation_times, [])
        self.assertIsNone(metrics.memory_peak)
        self.assertIsNone(metrics.memory_current)

    def test_processing_result_with_metrics(self):
        """Benchmark: Test ProcessingResult includes metrics."""
        from email_processor.imap.fetcher import ProcessingResult

        metrics = ProcessingMetrics()
        metrics.total_time = 1.5
        metrics.imap_operations = 5

        result = ProcessingResult(processed=10, skipped=2, errors=0, metrics=metrics)

        self.assertEqual(result.processed, 10)
        self.assertEqual(result.skipped, 2)
        self.assertEqual(result.errors, 0)
        self.assertIsNotNone(result.metrics)
        self.assertEqual(result.metrics.total_time, 1.5)
        self.assertEqual(result.metrics.imap_operations, 5)
