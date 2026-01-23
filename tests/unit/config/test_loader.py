"""Tests for config loader module."""

import unittest
from unittest.mock import MagicMock, mock_open, patch

from email_processor.config.loader import ConfigLoader, load_config, validate_config


class TestConfigValidation(unittest.TestCase):
    """Tests for configuration validation."""

    def test_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": 5,
                "retry_delay": 3,
            },
            "processing": {
                "start_days_back": 5,
                "log_level": "INFO",
            },
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {
                ".*test.*": "test_folder",
            },
        }
        # Should not raise
        validate_config(config)

    def test_imap_not_dict(self):
        """Test validation fails when imap is not a dictionary."""
        config = {
            "imap": "not a dict",
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'imap' must be a dictionary", str(context.exception))

    def test_processing_not_dict(self):
        """Test validation fails when processing is not a dictionary."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": "not a dict",
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'processing' must be a dictionary", str(context.exception))

    def test_missing_processing_section(self):
        """Test validation fails when processing section is missing."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("Missing required section: 'processing'", str(context.exception))

    def test_invalid_max_retries_type(self):
        """Test validation fails when max_retries is not an integer."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": "not a number",
            },
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'imap.max_retries' must be an integer", str(context.exception))

    def test_invalid_retry_delay_negative(self):
        """Test validation fails when retry_delay is negative."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "retry_delay": -1,
            },
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'imap.retry_delay' must be >= 0", str(context.exception))

    def test_invalid_retry_delay_type(self):
        """Test validation fails when retry_delay is not an integer."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "retry_delay": "not a number",
            },
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'imap.retry_delay' must be an integer", str(context.exception))

    def test_invalid_start_days_back_negative(self):
        """Test validation fails when start_days_back is negative."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {
                "start_days_back": -1,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'processing.start_days_back' must be >= 0", str(context.exception))

    def test_invalid_start_days_back_type(self):
        """Test validation fails when start_days_back is not an integer."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {
                "start_days_back": "not a number",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'processing.start_days_back' must be an integer", str(context.exception))

    def test_invalid_keep_processed_days_negative(self):
        """Test validation fails when keep_processed_days is negative."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {
                "keep_processed_days": -1,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'processing.keep_processed_days' must be >= 0", str(context.exception))

    def test_invalid_keep_processed_days_type(self):
        """Test validation fails when keep_processed_days is not an integer."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {
                "keep_processed_days": "not a number",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'processing.keep_processed_days' must be an integer", str(context.exception))

    def test_invalid_log_level(self):
        """Test validation fails when log_level is invalid."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {
                "log_level": "INVALID",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'processing.log_level' must be one of", str(context.exception))

    def test_allowed_senders_not_list(self):
        """Test validation fails when allowed_senders is not a list."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": "not a list",
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'allowed_senders' must be a list", str(context.exception))

    def test_allowed_senders_empty_warning(self):
        """Test that empty allowed_senders generates a warning (now uses print)."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
            "topic_mapping": {
                ".*": "default",
            },
        }
        # Now uses print instead of logging.warning (before logging is set up)
        # Just verify validation doesn't fail
        try:
            validate_config(config)
        except ValueError:
            self.fail("validate_config should not raise ValueError for empty allowed_senders")

    def test_allowed_senders_empty_warning_with_ui(self):
        """Test that empty allowed_senders uses ui.warn when ui is provided (covers line 83)."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
            "topic_mapping": {
                ".*": "default",
            },
        }
        mock_ui = MagicMock()
        # Should not raise ValueError
        validate_config(config, ui=mock_ui)
        # Should call ui.warn() instead of print()
        mock_ui.warn.assert_called_once()
        warning_call = mock_ui.warn.call_args[0][0]
        self.assertIn("allowed_senders", warning_call)
        self.assertIn("empty", warning_call)

    def test_topic_mapping_not_dict(self):
        """Test validation fails when topic_mapping is not a dictionary."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": "not a dict",
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'topic_mapping' must be a dictionary", str(context.exception))

    def test_topic_mapping_empty_dict(self):
        """Test validation fails when topic_mapping is empty."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'topic_mapping' must contain at least one rule", str(context.exception))

    def test_topic_mapping_empty_folder_name(self):
        """Test validation fails when folder name is empty."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*test.*": "",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("Invalid folder name", str(context.exception))

    def test_topic_mapping_non_string_folder(self):
        """Test validation fails when folder name is not a string."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*test.*": 123,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("Invalid folder name", str(context.exception))

    def test_missing_imap_section(self):
        """Test validation fails when imap section is missing."""
        config = {
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("Missing required section: 'imap'", str(context.exception))

    def test_missing_imap_server(self):
        """Test validation fails when imap.server is missing."""
        config = {
            "imap": {
                "user": "test@example.com",
            },
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'imap.server' is required", str(context.exception))

    def test_missing_imap_user(self):
        """Test validation fails when imap.user is missing."""
        config = {
            "imap": {
                "server": "imap.example.com",
            },
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'imap.user' is required", str(context.exception))

    def test_invalid_max_retries(self):
        """Test validation fails when max_retries is invalid."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": 0,
            },
            "processing": {},
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'imap.max_retries' must be >= 1", str(context.exception))

    def test_invalid_regex_pattern(self):
        """Test validation fails when topic_mapping has invalid regex."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                "[invalid": "folder",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("Invalid regex pattern", str(context.exception))

    def test_valid_smtp_config(self):
        """Test validation of valid SMTP configuration."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "use_tls": True,
                "from_address": "sender@example.com",
                "default_recipient": "recipient@example.com",
                "max_email_size": 25.0,
            },
        }
        # Should not raise
        validate_config(config)

    def test_smtp_not_dict(self):
        """Test validation fails when smtp is not a dictionary."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": "not a dict",
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp' must be a dictionary", str(context.exception))

    def test_smtp_missing_server(self):
        """Test validation fails when smtp.server is missing."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "port": 587,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.server' is required", str(context.exception))

    def test_smtp_empty_server(self):
        """Test validation fails when smtp.server is empty."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "",
                "port": 587,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.server' is required", str(context.exception))

    def test_smtp_invalid_port_type(self):
        """Test validation fails when smtp.port is not an integer."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "port": "not a number",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.port' must be an integer", str(context.exception))

    def test_smtp_port_too_low(self):
        """Test validation fails when smtp.port is less than 1."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "port": 0,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.port' must be between 1 and 65535", str(context.exception))

    def test_smtp_port_too_high(self):
        """Test validation fails when smtp.port is greater than 65535."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "port": 65536,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.port' must be between 1 and 65535", str(context.exception))

    def test_smtp_invalid_use_tls_type(self):
        """Test validation fails when smtp.use_tls is not a boolean."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "use_tls": "not a boolean",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.use_tls' must be a boolean", str(context.exception))

    def test_smtp_invalid_use_ssl_type(self):
        """Test validation fails when smtp.use_ssl is not a boolean."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "use_ssl": "not a boolean",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.use_ssl' must be a boolean", str(context.exception))

    def test_smtp_invalid_max_email_size_type(self):
        """Test validation fails when smtp.max_email_size is not a number."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "max_email_size": "not a number",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.max_email_size' must be a number", str(context.exception))

    def test_smtp_max_email_size_zero(self):
        """Test validation fails when smtp.max_email_size is zero."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "max_email_size": 0,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.max_email_size' must be > 0", str(context.exception))

    def test_smtp_max_email_size_negative(self):
        """Test validation fails when smtp.max_email_size is negative."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "max_email_size": -1,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.max_email_size' must be > 0", str(context.exception))

    def test_smtp_missing_from_address(self):
        """Test validation fails when smtp.from_address is missing."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.from_address' is required", str(context.exception))

    def test_smtp_empty_from_address(self):
        """Test validation fails when smtp.from_address is empty."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "from_address": "",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        # Empty string is treated as missing, so it checks for required field first
        self.assertIn("'smtp.from_address'", str(context.exception))

    def test_smtp_invalid_from_address_type(self):
        """Test validation fails when smtp.from_address is not a string."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "from_address": 123,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.from_address' must be a non-empty string", str(context.exception))

    def test_smtp_invalid_from_address_format(self):
        """Test validation fails when smtp.from_address has invalid email format."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "from_address": "invalid-email",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.from_address' must be a valid email address", str(context.exception))

    def test_smtp_invalid_default_recipient_type(self):
        """Test validation fails when smtp.default_recipient is not a string."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "from_address": "sender@example.com",
                "default_recipient": 123,
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.default_recipient' must be a non-empty string", str(context.exception))

    def test_smtp_empty_default_recipient(self):
        """Test validation fails when smtp.default_recipient is empty."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "from_address": "sender@example.com",
                "default_recipient": "",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("'smtp.default_recipient' must be a non-empty string", str(context.exception))

    def test_smtp_invalid_default_recipient_format(self):
        """Test validation fails when smtp.default_recipient has invalid email format."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
            "smtp": {
                "server": "smtp.example.com",
                "from_address": "sender@example.com",
                "default_recipient": "invalid-email",
            },
        }
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn(
            "'smtp.default_recipient' must be a valid email address", str(context.exception)
        )


class TestLoadConfig(unittest.TestCase):
    """Tests for configuration loading."""

    def test_load_valid_config(self):
        """Test loading valid YAML configuration."""
        config_content = """
imap:
  server: "imap.example.com"
  user: "test@example.com"
processing:
  start_days_back: 5
"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", mock_open(read_data=config_content)):
                with patch("email_processor.config.loader.validate_config"):
                    config = load_config("config.yaml")
                    self.assertIn("imap", config)
                    self.assertEqual(config["imap"]["server"], "imap.example.com")

    def test_load_nonexistent_file(self):
        """Test loading non-existent configuration file."""
        with self.assertRaises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML."""
        config_content = "invalid: yaml: content: ["
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", mock_open(read_data=config_content)):
                with self.assertRaises(ValueError):
                    load_config("config.yaml")

    def test_load_config_io_error(self):
        """Test loading config with IO error."""
        from pathlib import Path as PathClass

        mock_path = MagicMock(spec=PathClass)
        mock_path.exists.return_value = True
        # Make open() raise IOError when called (as a context manager)
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = OSError("Permission denied")
        mock_path.open.return_value = mock_context
        with patch("email_processor.config.loader.Path", return_value=mock_path):
            with self.assertRaises(IOError):
                load_config("config.yaml")

    def test_load_config_not_dict(self):
        """Test loading config that is not a dictionary."""
        # YAML string that loads to a string, not a dict
        config_content = "just a string"
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", mock_open(read_data=config_content)):
                with self.assertRaises(TypeError) as context:
                    load_config("config.yaml")
                self.assertIn("must contain a top-level YAML object", str(context.exception))


class TestConfigLoader(unittest.TestCase):
    """Tests for ConfigLoader class."""

    def test_config_loader_load(self):
        """Test ConfigLoader.load method."""
        config_content = """
imap:
  server: "imap.example.com"
  user: "test@example.com"
processing:
  start_days_back: 5
"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", mock_open(read_data=config_content)):
                with patch("email_processor.config.loader.validate_config"):
                    config = ConfigLoader.load("config.yaml")
                    self.assertIn("imap", config)

    def test_config_loader_validate(self):
        """Test ConfigLoader.validate method."""
        config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "topic_mapping": {
                ".*": "default",
            },
        }
        # Should not raise
        ConfigLoader.validate(config)
