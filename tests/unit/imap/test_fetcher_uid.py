"""Tests for Fetcher uid functionality."""

from unittest.mock import MagicMock, patch

from tests.unit.imap.test_fetcher_base import TestFetcherBase


class TestFetcherUID(TestFetcherBase):
    """Tests for Fetcher uid functionality."""

    def test_process_email_uid_parse_error_attribute_error(self):
        """Test _process_email when UID parsing raises AttributeError."""
        mock_mail = MagicMock()
        # Return meta data that will cause AttributeError when trying to access meta[0][0]
        mock_meta_item = MagicMock()
        # Make meta[0] not None, but accessing meta[0][0] will raise AttributeError
        del mock_meta_item.__getitem__
        mock_mail.fetch.side_effect = [
            (
                "OK",
                [(mock_meta_item, None)],
            ),  # meta[0] exists but accessing [0] raises AttributeError
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_parse_error_index_error(self):
        """Test _process_email when UID parsing raises IndexError."""
        mock_mail = MagicMock()
        # Return meta data that will cause IndexError when trying to access meta[0][0]
        mock_meta_item = []
        mock_mail.fetch.side_effect = [
            (
                "OK",
                [(mock_meta_item, None)],
            ),  # meta[0] exists but is empty list, accessing [0] raises IndexError
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_parse_error_unicode_decode_error(self):
        """Test _process_email when UID parsing raises UnicodeDecodeError."""
        from email_processor.imap.fetcher import ProcessingMetrics

        mock_mail = MagicMock()

        # Return meta data that will cause UnicodeDecodeError when trying to decode
        # Create a mock that when accessed returns bytes that can't be decoded
        class BadDecode:
            def decode(self, encoding, errors="strict"):
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

        mock_meta_item = BadDecode()
        mock_mail.fetch.side_effect = [
            ("OK", [(mock_meta_item, None)]),
        ]

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_parse_unexpected_error(self):
        """Test _process_email when UID parsing raises unexpected error."""
        mock_mail = MagicMock()
        # Return meta data that will cause unexpected error
        mock_meta = MagicMock()
        mock_meta.__getitem__ = MagicMock(side_effect=RuntimeError("Unexpected error"))
        mock_mail.fetch.side_effect = [
            ("OK", [(mock_meta, None)]),
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_failed_uid_save_error(self):
        """Test _process_email when message fetch fails and UID save also fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("NO", None),  # Message fetch fails
        ]

        # Mock save_processed_uid_for_day to raise OSError
        with patch(
            "email_processor.imap.fetcher.save_processed_uid_for_day",
            side_effect=OSError("Permission denied"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle the error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_failed_uid_save_unexpected_error(self):
        """Test _process_email when message fetch fails and UID save raises unexpected error."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("NO", None),  # Message fetch fails
        ]

        # Mock save_processed_uid_for_day to raise unexpected error
        with patch(
            "email_processor.imap.fetcher.save_processed_uid_for_day",
            side_effect=ValueError("Unexpected error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle the error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_uid_fetch_data_error_attribute_error(self):
        """Test _process_email when UID fetch returns data with AttributeError."""
        mock_mail = MagicMock()

        # Create a mock that raises AttributeError when accessing fetch result
        class MockFetchResult:
            def __getitem__(self, key):
                raise AttributeError("No attribute")

        mock_mail.fetch.return_value = ("OK", MockFetchResult())

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_fetch_data_error_index_error(self):
        """Test _process_email when UID fetch returns data with IndexError."""
        mock_mail = MagicMock()

        # Create a mock that raises IndexError when accessing meta[0]
        class MockFetchResult:
            def __getitem__(self, key):
                if key == 0:
                    raise IndexError("List index out of range")

        mock_mail.fetch.return_value = ("OK", MockFetchResult())

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_fetch_data_error_type_error(self):
        """Test _process_email when UID fetch returns data with TypeError."""
        mock_mail = MagicMock()

        # Create a mock that raises TypeError when accessing fetch result
        class MockFetchResult:
            def __getitem__(self, key):
                raise TypeError("Unsupported type")

        mock_mail.fetch.return_value = ("OK", MockFetchResult())

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)
