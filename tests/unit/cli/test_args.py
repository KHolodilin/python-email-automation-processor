"""Tests for CLI argument parsing."""

import unittest
from unittest.mock import patch

from email_processor.cli.args import parse_arguments


class TestParseArguments(unittest.TestCase):
    """Tests for _parse_arguments function."""

    def test_parse_arguments_default(self):
        """Test parsing arguments with default values (no command = run)."""
        with patch("sys.argv", ["email_processor"]):
            args = parse_arguments()
            self.assertIsNone(args.command)  # Defaults to run
            self.assertFalse(args.dry_run)
            self.assertIsNotNone(args.config)

    def test_parse_arguments_password_clear(self):
        """Test parsing password clear command."""
        with patch(
            "sys.argv", ["email_processor", "password", "clear", "--user", "test@example.com"]
        ):
            args = parse_arguments()
            self.assertEqual(args.command, "password")
            self.assertEqual(args.password_command, "clear")
            self.assertEqual(args.user, "test@example.com")

    def test_parse_arguments_password_set(self):
        """Test parsing password set command."""
        with patch(
            "sys.argv",
            [
                "email_processor",
                "password",
                "set",
                "--user",
                "test@example.com",
                "--password-file",
                "test.txt",
            ],
        ):
            args = parse_arguments()
            self.assertEqual(args.command, "password")
            self.assertEqual(args.password_command, "set")
            self.assertEqual(args.user, "test@example.com")
            self.assertEqual(args.password_file, "test.txt")

    def test_parse_arguments_password_set_delete_after_read(self):
        """Test parsing password set with --delete-after-read."""
        with patch(
            "sys.argv",
            [
                "email_processor",
                "password",
                "set",
                "--user",
                "test@example.com",
                "--password-file",
                "test.txt",
                "--delete-after-read",
            ],
        ):
            args = parse_arguments()
            self.assertTrue(args.delete_after_read)

    def test_parse_arguments_password_set_without_user(self):
        """Test parsing password set without --user (optional, fallback from config)."""
        with patch(
            "sys.argv",
            ["email_processor", "password", "set", "--password-file", "p.txt"],
        ):
            args = parse_arguments()
            self.assertEqual(args.command, "password")
            self.assertEqual(args.password_command, "set")
            self.assertIsNone(args.user)
            self.assertEqual(args.password_file, "p.txt")

    def test_parse_arguments_dry_run(self):
        """Test parsing --dry-run argument."""
        with patch("sys.argv", ["email_processor", "run", "--dry-run"]):
            args = parse_arguments()
            self.assertTrue(args.dry_run)

    def test_parse_arguments_dry_run_no_connect(self):
        """Test parsing --dry-run-no-connect argument."""
        with patch("sys.argv", ["email_processor", "run", "--dry-run-no-connect"]):
            args = parse_arguments()
            self.assertTrue(args.dry_run_no_connect)

    def test_parse_arguments_config(self):
        """Test parsing --config argument."""
        with patch("sys.argv", ["email_processor", "run", "--config", "custom.yaml"]):
            args = parse_arguments()
            self.assertEqual(args.config, "custom.yaml")

    def test_parse_arguments_config_init(self):
        """Test parsing config init command."""
        with patch("sys.argv", ["email_processor", "config", "init"]):
            args = parse_arguments()
            self.assertEqual(args.command, "config")
            self.assertEqual(args.config_command, "init")

    def test_parse_arguments_send_file(self):
        """Test parsing send file command."""
        with patch(
            "sys.argv", ["email_processor", "send", "file", "file.txt", "--to", "test@example.com"]
        ):
            args = parse_arguments()
            self.assertEqual(args.command, "send")
            self.assertEqual(args.send_command, "file")
            self.assertEqual(args.path, "file.txt")
            self.assertEqual(args.to, "test@example.com")

    def test_parse_arguments_send_folder(self):
        """Test parsing send folder command."""
        with patch(
            "sys.argv", ["email_processor", "send", "folder", "folder", "--to", "test@example.com"]
        ):
            args = parse_arguments()
            self.assertEqual(args.command, "send")
            self.assertEqual(args.send_command, "folder")
            self.assertEqual(args.dir, "folder")
            self.assertEqual(args.to, "test@example.com")

    def test_parse_arguments_send_folder_no_args(self):
        """Test parsing send folder without dir/--to (optional, use config defaults)."""
        with patch("sys.argv", ["email_processor", "send", "folder"]):
            args = parse_arguments()
            self.assertEqual(args.command, "send")
            self.assertEqual(args.send_command, "folder")
            self.assertIsNone(args.dir)
            self.assertIsNone(args.to)

    def test_parse_arguments_send_subject(self):
        """Test parsing --subject argument for send."""
        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "file",
                "file.txt",
                "--to",
                "test@example.com",
                "--subject",
                "Test Subject",
            ],
        ):
            args = parse_arguments()
            self.assertEqual(args.subject, "Test Subject")

    def test_parse_arguments_version(self):
        """Test parsing --version argument."""
        with patch("sys.argv", ["email_processor", "--version"]):
            with self.assertRaises(SystemExit):
                parse_arguments()

    def test_parse_arguments_verbose_and_quiet_mutually_exclusive(self):
        """Test that --verbose and --quiet cannot be used together (covers line 311)."""
        with patch("sys.argv", ["email_processor", "--verbose", "--quiet"]):
            with self.assertRaises(SystemExit) as cm:
                parse_arguments()
            # argparse raises SystemExit(2) for argument errors
            self.assertEqual(cm.exception.code, 2)
