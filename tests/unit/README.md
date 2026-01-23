# Структура тестов

Структура тестов соответствует структуре основного проекта `email_processor`:

```
tests/unit/
├── cli/                    # Тесты для email_processor/cli/
│   ├── test_args.py        # Тесты для email_processor/cli/args.py
│   ├── test_ui.py          # Тесты для email_processor/cli/ui.py
│   └── commands/           # Тесты для email_processor/cli/commands/
│       ├── test_config.py  # Тесты для email_processor/cli/commands/config.py
│       ├── test_passwords.py # Тесты для email_processor/cli/commands/passwords.py
│       └── test_smtp.py    # Тесты для email_processor/cli/commands/smtp.py
├── config/                 # Тесты для email_processor/config/
│   └── test_loader.py
├── imap/                   # Тесты для email_processor/imap/
│   ├── test_archive.py
│   ├── test_attachments.py
│   ├── test_auth.py
│   ├── test_client.py
│   ├── test_fetcher.py
│   ├── test_fetcher_base.py         # Базовый класс для тестов Fetcher
│   ├── test_fetcher_header.py       # Тесты обработки заголовков
│   ├── test_fetcher_message.py      # Тесты обработки сообщений
│   ├── test_fetcher_uid.py          # Тесты обработки UID
│   ├── test_fetcher_attachment.py   # Тесты обработки вложений
│   ├── test_fetcher_archive.py      # Тесты архивирования
│   ├── test_fetcher_storage.py      # Тесты сохранения обработанных UID
│   ├── test_fetcher_file_ops.py    # Тесты файловых операций
│   ├── test_fetcher_errors.py       # Тесты обработки ошибок
│   └── test_filters.py
├── logging/                # Тесты для email_processor/logging/
│   ├── test_formatters.py
│   └── test_setup.py
├── security/               # Тесты для email_processor/security/
│   ├── test_encryption.py
│   ├── test_fingerprint.py
│   └── test_key_generator.py
├── smtp/                   # Тесты для email_processor/smtp/
│   ├── test_client.py
│   ├── test_sender.py
│   └── test_sent_files_storage.py
├── storage/                # Тесты для email_processor/storage/
│   ├── test_file_manager.py
│   └── test_uid_storage.py
├── utils/                  # Тесты для email_processor/utils/
│   ├── test_context.py
│   ├── test_disk_utils.py
│   ├── test_email_utils.py
│   ├── test_folder_resolver.py
│   └── test_path_utils.py
└── test_main.py            # Тесты для email_processor/__main__.py
```

## Соответствие файлов

| Исходный файл проекта | Файл теста |
|----------------------|------------|
| `email_processor/cli/args.py` | `tests/unit/cli/test_args.py` |
| `email_processor/cli/ui.py` | `tests/unit/cli/test_ui.py` |
| `email_processor/cli/commands/config.py` | `tests/unit/cli/commands/test_config.py` |
| `email_processor/cli/commands/passwords.py` | `tests/unit/cli/commands/test_passwords.py` |
| `email_processor/cli/commands/smtp.py` | `tests/unit/cli/commands/test_smtp.py` |
| `email_processor/__main__.py` | `tests/unit/test_main.py` |
| `email_processor/imap/fetcher.py` | `tests/unit/imap/test_fetcher.py`<br>`tests/unit/imap/test_fetcher_*.py` (дополнительные тесты) |
| `email_processor/imap/attachments.py` | `tests/unit/imap/test_attachments.py` |
| `email_processor/imap/filters.py` | `tests/unit/imap/test_filters.py` |
