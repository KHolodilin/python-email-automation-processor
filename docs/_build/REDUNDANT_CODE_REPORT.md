# Отчёт: лишние файлы, классы и методы

## 1. Файлы

| Файл | Проблема | Рекомендация |
|------|----------|--------------|
| **`40.0`** (корень) | Пустой файл, похож на артефакт (версия cryptography?) | **Удалить** и добавить в `.gitignore` при необходимости |
| **`tests/run_all_tests.py`** | Обёртка над `pytest` с `--cov` и `--cov-fail-under=95` | Оставить: удобная точка входа, упоминается в `run_tests.bat` |

---

## 2. Классы-обёртки (в проде не используются)

Во всех случаях **production-код** использует только **модульные функции**. Классы есть в API и тестах, но не в основном коде.

| Класс | Модуль | Фактическое использование в коде | Рекомендация |
|-------|--------|-----------------------------------|--------------|
| **PathUtils** | `utils.path_utils` | Только тесты. Функции `normalize_folder_name`, `sanitize_filename` в проде **вообще не вызываются** (`file_manager` использует `os.path.basename`) | Класс лишний; функции можно пометить deprecated или начать использовать |
| **EmailUtils** | `utils.email_utils` | В проде используются только `decode_mime_header_value`, `parse_email_date`. `extract_sender`, `extract_subject` — **нигде** | Класс лишний; `extract_*` можно удалить или оставить только в тестах |
| **DiskUtils** | `utils.disk_utils` | В проде только `check_disk_space`. Класс и `get_free_space` — только тесты | Класс лишний |
| **FolderResolver** | `utils.folder_resolver` | В проде только `resolve_custom_folder` (через `EmailFilter`). Класс — только тесты | Класс лишний |
| **FileManager** | `storage.file_manager` | В проде только `safe_save_path`, `validate_path`. Класс и `ensure_directory` — только тесты | Класс лишний |
| **LoggingManager** | `logging.setup` | Везде используются `get_logger`, `setup_logging`. Класс — только в тестах и `logging/__init__.py` | Класс лишний |
| **ArchiveManager** | `imap.archive` | В проде только `archive_message` (fetcher). Класс — тесты и `imap/__init__.py` | Класс лишний |

**Важно:** все эти классы экспортируются в `__init__.py` (utils, storage, logging, imap) и могут быть частью публичного API. Удаление — **breaking change** для тех, кто импортирует классы.

---

## 3. Методы, не используемые в проде

| Метод | Использование | Рекомендация |
|-------|----------------|--------------|
| **EmailUtils.extract_sender** | Только тесты | Удалить или оставить как утилиту |
| **EmailUtils.extract_subject** | Только тесты | Аналогично |
| **DiskUtils.get_free_space** | Только тесты | Удалить или оставить |
| **FileManager.ensure_directory** | Только тесты | Удалить или оставить |
| **FolderResolver._compile_pattern** | Только тест; дублирует модульную `_compile_pattern` | Удалить метод, тест переписать на модульную функцию |

---

## 4. Модули / код, не используемые в production

| Модуль / код | Где используется | Рекомендация |
|--------------|------------------|--------------|
| **`logging/formatters.py`** (`StructlogFileFormatter`) | Только в `tests/unit/logging/test_formatters.py`. `setup_logging` использует `structlog.stdlib.ProcessorFormatter` | Форматер в проде не используется. **Удалить** модуль и тесты или оставить «на будущее» |
| **`normalize_folder_name`**, **`sanitize_filename`** | Экспортируются в `utils`, но **нигде не вызываются** в `email_processor` | Либо начать использовать (напр. в `file_manager`), либо deprecate/удалить |

---

## 5. Что не является лишним

- **`test_ui.py`** vs **`test_ui_cliui.py`**: разные цели. `test_ui` — main + интеграция с UI; `test_ui_cliui` — юнит-тесты самого `CLIUI`. Оба имеют смысл.
- **`ConfigLoader`** и **`load_config`**: оба используются (`ConfigLoader.load` — в __main__, config, status; `load_config` — в тестах). Не дубликаты.
- **`download_attachments`**, **`EmailProcessor`**: legacy API в `__init__.py`, используются (напр. `test_full_cycle_integration`, `cli/commands/imap`). Оставлять для обратной совместимости.

---

## 6. Рекомендуемые шаги (по приоритету)

1. **Сразу:** удалить файл **`40.0`**.
2. **Низкий риск:** удалить **`FolderResolver._compile_pattern`** и упростить тест (вызывать модульную `_compile_pattern` или не тестировать отдельно).
3. **Средний риск:** перестать экспортировать/использовать **`StructlogFileFormatter`** (и при необходимости удалить `formatters.py` и связанные тесты), если не планируется использование.
4. **Высокий риск (breaking changes):** удаление классов-обёрток (**PathUtils**, **EmailUtils**, **DiskUtils**, **FolderResolver**, **FileManager**, **LoggingManager**, **ArchiveManager**) и переход на использование только функций. Требует обновления тестов и, при наличии внешних пользователей, миграции импортов.

Если нужно, могу предложить конкретные патчи (пошагово) для пунктов 1–3.
