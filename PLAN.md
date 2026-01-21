# План работ по улучшению проекта

## Структура плана
Каждая задача включает:
1. Создание GitHub Issue
2. Создание ветки `feature/issue-{номер}-{название}`
3. **Переход на новую ветку** (вручную): `git checkout -b feature/issue-{номер}-{название}`
4. Реализацию изменений
5. Тестирование и проверки
6. Коммит изменений
7. **Поднять версию** в `pyproject.toml` перед созданием PR (patch version: 7.4.X → 7.4.X+1)
8. **Push ветки** (вручную): `git push origin feature/issue-{номер}-{название}`
9. **Создание Pull Request** с веткой `main`/`master`

---

## Issue #1: Интеграция с Codecov

**Title (EN):** Integrate Codecov for coverage reporting

**Description (EN):** Improve Codecov integration in CI/CD pipeline. Currently, Codecov action is present but may not be fully configured. Enhance the integration to ensure proper coverage reporting, add coverage thresholds, and configure Codecov settings for better visibility and reporting.

### Ветка: `feature/issue-1-integrate-codecov`

### Задачи:
- [ ] Улучшить настройку Codecov в CI workflow
  - Проверить корректность генерации `coverage.xml`
  - Добавить флаг `--cov-report=xml` в pytest для генерации XML отчета
  - Настроить правильные параметры для codecov-action
  - Добавить токен Codecov (если требуется)
- [ ] Добавить конфигурацию Codecov
  - Создать `codecov.yml` для настройки поведения Codecov
  - Настроить минимальный порог покрытия
  - Настроить уведомления о падении покрытия
- [ ] Добавить проверку покрытия в CI
  - Добавить `--cov-fail-under` для проверки минимального покрытия
  - Настроить fail при падении покрытия ниже порога
- [ ] Обновить документацию
  - Добавить информацию о Codecov в README
  - Добавить ссылку на Codecov dashboard

### По окончанию:
```bash
# Тестирование и проверки
pytest --cov=email_processor --cov-report=xml --cov-report=term-missing
# Проверить, что coverage.xml создается
# Проверить, что Codecov получает данные

# Коммит
git add .
git commit -m "ci: integrate Codecov for coverage reporting

Fixes #1"

# Push и создание PR (вручную)
git push origin feature/issue-1-integrate-codecov
# Затем создать Pull Request через GitHub UI или CLI
```

---

## Issue #2: Улучшение покрытия тестами до 95%

**Title (EN):** Improve test coverage to 95%+

**Description (EN):** Increase test coverage from current level to at least 95% by adding comprehensive tests for all modules. This will improve code reliability, maintainability, and ensure better code quality through extensive testing.

### Ветка: `feature/issue-2-improve-test-coverage-95`

### Задачи:
- [ ] Провести анализ текущего покрытия
  - Запустить `pytest --cov=email_processor --cov-report=term-missing`
  - Определить модули с низким покрытием
  - Составить список недостающих тестов
- [ ] Добавить тесты для модулей с низким покрытием
  - Тесты для всех публичных методов и классов
  - Тесты для edge cases и граничных условий
  - Тесты для обработки ошибок
  - Тесты для всех веток кода (if/else, try/except)
- [ ] Добавить интеграционные тесты
  - Тесты для полного цикла обработки
  - Тесты для взаимодействия между модулями
  - Тесты для реальных сценариев использования
- [ ] Настроить проверку покрытия в CI
  - Добавить `--cov-fail-under=95` в pytest команду
  - Убедиться, что CI падает при покрытии ниже 95%
- [ ] Обновить документацию по тестированию
  - Обновить `README_TESTS.md` с информацией о покрытии
  - Добавить инструкции по запуску тестов с покрытием

### Цель покрытия: ≥95%

### По окончанию:
```bash
# Тестирование и проверки
pytest --cov=email_processor --cov-report=term-missing --cov-fail-under=95
pre-commit run --all-files
python -m email_processor --version  # Проверка работоспособности

# Коммит
git add .
git commit -m "test: improve test coverage to 95%+

Fixes #2"

# Push и создание PR (вручную)
git push origin feature/issue-2-improve-test-coverage-95
# Затем создать Pull Request через GitHub UI или CLI
```

---

## Issue #3: Добавление документации проекта (Code of Conduct, License, Security Policy, Templates)

**Title (EN):** Add project documentation and templates (Code of Conduct, License, Security Policy, Issue/PR templates)

**Description (EN):** Add essential project documentation files including Code of Conduct, License file, Security Policy, and GitHub templates for issues and pull requests. This will improve project professionalism, provide clear guidelines for contributors, and streamline the contribution process.

### Ветка: `feature/issue-3-add-project-documentation`

### Задачи:
- [ ] Добавить LICENSE файл
  - Выбрать лицензию (MIT, Apache 2.0, или другая)
  - Создать `LICENSE` файл с полным текстом лицензии
  - Обновить `pyproject.toml` если нужно (уже указано MIT)
- [ ] Добавить CODE_OF_CONDUCT.md
  - Использовать Contributor Covenant или создать собственный
  - Добавить информацию о том, как сообщать о нарушениях
  - Добавить контактную информацию
- [ ] Добавить SECURITY.md (Security Policy)
  - Описать процесс сообщения об уязвимостях
  - Указать поддерживаемые версии
  - Добавить информацию о процессе исправления
  - Создать в `.github/SECURITY.md` или в корне проекта
- [ ] Создать Issue templates
  - Создать `.github/ISSUE_TEMPLATE/` директорию
  - Добавить шаблон для bug reports (`bug_report.md`)
  - Добавить шаблон для feature requests (`feature_request.md`)
  - Добавить шаблон для вопросов (`question.md`) - опционально
  - Настроить `config.yml` для выбора шаблона
- [ ] Создать Pull Request template
  - Создать `.github/pull_request_template.md`
  - Добавить секции: описание, тип изменений, проверки, связанные issues
  - Добавить чеклист для проверки перед PR

### По окончанию:
```bash
# Проверка файлов
# Убедиться, что все файлы созданы и корректны
# Проверить форматирование Markdown

# Коммит
git add .
git commit -m "docs: add Code of Conduct, License, Security Policy, and templates

- Add LICENSE file
- Add CODE_OF_CONDUCT.md
- Add SECURITY.md
- Add GitHub issue templates
- Add pull request template

Fixes #3"

# Push и создание PR (вручную)
git push origin feature/issue-3-add-project-documentation
# Затем создать Pull Request через GitHub UI или CLI
```

---

## Issue #4: Добавление бейджей в README

**Title (EN):** Add project badges to README

**Description (EN):** Add professional project badges to README.md to display project status, version, test coverage, CI status, and other important metrics. This will improve project visibility and provide quick access to key project information.

### Ветка: `feature/issue-4-add-readme-badges`

### Задачи:
- [ ] Добавить бейджи в начало README.md
  - PyPI version badge: `[![PyPI](https://img.shields.io/pypi/v/email-processor)](https://pypi.org/project/email-processor/)`
  - CI status badge: `[![CI](https://github.com/vkholodilin/python-email-automation-processor/actions/workflows/ci.yml/badge.svg)](https://github.com/vkholodilin/python-email-automation-processor/actions/workflows/ci.yml)`
  - Test Coverage badge: `[![Test Coverage](https://codecov.io/gh/vkholodilin/python-email-automation-processor/branch/main/graph/badge.svg)](https://codecov.io/gh/vkholodilin/python-email-automation-processor)`
  - Python version badge: `[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)`
  - License badge: `[![License](https://img.shields.io/github/license/vkholodilin/python-email-automation-processor)](LICENSE)`
  - Stars badge: `[![Stars](https://img.shields.io/github/stars/vkholodilin/python-email-automation-processor)](https://github.com/vkholodilin/python-email-automation-processor/stargazers)`
  - Code style badge (Ruff): `[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)`
- [ ] Проверить корректность ссылок
  - Убедиться, что все ссылки указывают на правильные репозитории
  - Проверить, что бейджи отображаются корректно
  - Проверить работу бейджей после merge в main
- [ ] Форматирование
  - Разместить бейджи в логичном порядке
  - Добавить пустую строку после бейджей для читаемости
  - Убедиться, что бейджи не нарушают структуру README

### По окончанию:
```bash
# Проверка
# Открыть README.md и проверить отображение бейджей
# Убедиться, что все ссылки корректны

# Коммит
git add .
git commit -m "docs: add project badges to README

- Add PyPI version badge
- Add CI status badge
- Add test coverage badge
- Add Python version badge
- Add license badge
- Add stars badge
- Add code style badge (Ruff)

Fixes #4"

# Push и создание PR (вручную)
git push origin feature/issue-4-add-readme-badges
# Затем создать Pull Request через GitHub UI или CLI
```

---

## Issue #5: Стандартизация exit codes в CLI

**Title (EN):** Standardize CLI exit codes

**Description (EN):** Implement standardized exit codes for the CLI to provide clear error reporting and better integration with scripts and automation tools. Define and document exit codes for different error scenarios to improve user experience and enable proper error handling in automated workflows.

### Ветка: `feature/issue-5-standardize-exit-codes`

### Задачи:
- [ ] Определить константы для exit codes
  - Создать модуль `email_processor/constants.py` или добавить в существующий
  - Определить константы для всех exit codes:
    - `EXIT_SUCCESS = 0`
    - `EXIT_PROCESSING_ERROR = 1`
    - `EXIT_VALIDATION_FAILED = 2`
    - `EXIT_FILE_NOT_FOUND = 3`
    - `EXIT_UNSUPPORTED_FORMAT = 4`
    - `EXIT_WARNINGS_AS_ERRORS = 5`
    - `EXIT_CONFIG_ERROR = 6`
- [ ] Обновить код CLI для использования стандартных exit codes
  - Заменить все `return 1` на соответствующие константы
  - Определить правильные exit codes для каждого типа ошибки:
    - Ошибки обработки (extraction/parsing/mapping/write) → 1
    - Ошибки валидации (в strict mode) → 2
    - Файл не найден → 3
    - Неподдерживаемый формат → 4
    - Warnings as errors (--fail-on-warnings) → 5
    - Ошибки конфигурации → 6
- [ ] Добавить документацию exit codes в README
  - Создать раздел "Exit Codes" в README
  - Описать каждый exit code и когда он используется
  - Добавить примеры использования в скриптах
- [ ] Добавить тесты для exit codes
  - Тесты для каждого типа exit code
  - Проверка корректности возвращаемых кодов
  - Интеграционные тесты для различных сценариев

### Стандартные exit codes:
- `0`: Success
- `1`: Processing error (extraction/parsing/mapping/write error)
- `2`: Validation failed (in strict mode)
- `3`: Input file not found
- `4`: Unsupported format (cannot detect form type)
- `5`: Warnings as errors (--fail-on-warnings enabled)
- `6`: Configuration error

### По окончанию:
```bash
# Тестирование и проверки
pytest tests/ -v
# Проверить различные сценарии и их exit codes
python -m email_processor --version  # Должен вернуть 0
python -m email_processor --config nonexistent.yaml  # Должен вернуть 6
# и т.д.

# Коммит
git add .
git commit -m "feat: standardize CLI exit codes

- Add exit code constants
- Update CLI to use standardized exit codes
- Add exit codes documentation to README
- Add tests for exit codes

Fixes #5"

# Push и создание PR (вручную)
git push origin feature/issue-5-standardize-exit-codes
# Затем создать Pull Request через GitHub UI или CLI
```

---

## Issue #6: Добавление Quickstart раздела в README

**Title (EN):** Add Quickstart section to README

**Description (EN):** Add a Quickstart section to README.md to help new users get started quickly with the project. This section should provide a concise guide for installation and basic usage, making it easier for users to understand and use the project.

### Ветка: `feature/issue-6-add-quickstart-section`

### Задачи:
- [ ] Добавить раздел Quickstart в README.md
  - Разместить после заголовка и описания, но перед детальными разделами
  - Включить минимальные шаги для быстрого старта
  - Добавить примеры основных команд
- [ ] Структура Quickstart раздела:
  - Краткое описание (1-2 предложения)
  - Установка (pip install или из исходников)
  - Создание конфигурации (--create-config)
  - Базовый пример использования
  - Ссылки на детальную документацию
- [ ] Добавить примеры кода
  - Пример минимальной конфигурации
  - Пример запуска обработки
  - Пример отправки файла через SMTP
- [ ] Обновить структуру README
  - Убедиться, что Quickstart логично вписывается в структуру
  - Добавить навигацию или ссылки на детальные разделы
  - Проверить читаемость и последовательность

### По окончанию:
```bash
# Проверка
# Открыть README.md и проверить:
# - Корректность форматирования
# - Работоспособность примеров кода
# - Логичность структуры
# - Ссылки на детальные разделы

# Коммит
git add .
git commit -m "docs: add Quickstart section to README

- Add Quickstart section with installation and basic usage
- Add code examples for common use cases
- Improve README structure and navigation

Fixes #6"

# Push и создание PR (вручную)
git push origin feature/issue-6-add-quickstart-section
# Затем создать Pull Request через GitHub UI или CLI
```

---

## Общий порядок выполнения

1. **Issue #1** - Интеграция с Codecov (базовая инфраструктура для отслеживания покрытия)
2. **Issue #2** - Улучшение покрытия тестами до 95% (требует работающего Codecov)
3. **Issue #3** - Добавление документации проекта (независимая задача)
4. **Issue #4** - Добавление бейджей в README (финальный штрих, требует работающего CI и Codecov)
5. **Issue #5** - Стандартизация exit codes в CLI (улучшение UX и автоматизации)
6. **Issue #6** - Добавление Quickstart раздела в README (улучшение документации)

**Примечание:**
- Issue #1 и Issue #2 связаны - сначала нужно настроить Codecov, затем поднять покрытие
- Issue #3 и Issue #4 можно выполнять параллельно или в любом порядке
- Issue #5 и Issue #6 независимы и могут выполняться в любом порядке
- Issue #6 логично выполнять после Issue #4 (бейджи), чтобы Quickstart был в финальной версии README

---

## Шаблон для создания Issue в GitHub

**Важно:** Все описание issue должно быть полностью на английском языке.

```markdown
## Description
[English description from plan]

## Tasks
- [ ] Task 1
- [ ] Task 2
- [ ] ...

## Acceptance Criteria
- [ ] All tests pass
- [ ] Pre-commit checks pass
- [ ] Test coverage meets requirements (if applicable)
- [ ] Code committed
- [ ] Branch pushed to remote repository
- [ ] Pull Request created with main branch
```

**Примечание:** Раздел "Branch" не нужно включать в описание issue. Ветка создается автоматически по шаблону `feature/issue-{номер}-{название}`.

## Шаги выполнения

1. **Создать и перейти на ветку** (вручную):
   ```bash
   git checkout -b feature/issue-{номер}-{название}
   ```

2. Выполнить задачи из списка выше

3. После завершения работы:
   ```bash
   # Тестирование
   pytest --cov=email_processor --cov-report=term-missing
   pre-commit run --all-files
   python -m email_processor --version  # Проверка работоспособности

   # Коммит
   git add .
   git commit -m "{type}: {description}

   Fixes #{номер}"

   # Push (вручную)
   git push origin feature/issue-{номер}-{название}
   ```

4. **Создать Pull Request** через GitHub UI или CLI (вручную)

---

## Шаблон коммита

```
{type}({scope}): {subject}

{body}

Fixes #{issue_number}
```

Типы:
- `feat`: новая функциональность
- `fix`: исправление бага
- `test`: добавление/изменение тестов
- `refactor`: рефакторинг кода
- `ci`: изменения в CI/CD
- `docs`: изменения в документации

---

## Дополнительные заметки

### Для Issue #1 (Codecov):
- Убедиться, что в CI workflow генерируется `coverage.xml`
- Проверить настройки репозитория в Codecov (если требуется регистрация)
- Возможно потребуется добавить токен Codecov в GitHub Secrets

### Для Issue #2 (95% покрытие):
- Начать с модулей с наименьшим покрытием
- Использовать `--cov-report=term-missing` для определения непокрытых строк
- Добавлять тесты постепенно, проверяя покрытие после каждого модуля

### Для Issue #3 (Документация):
- Можно использовать готовые шаблоны от GitHub
- Contributor Covenant - популярный выбор для Code of Conduct
- Security Policy можно разместить в `.github/SECURITY.md` или в корне проекта

### Для Issue #4 (Бейджи):
- Бейджи будут работать только после merge в main и настройки Codecov
- Некоторые бейджи требуют, чтобы репозиторий был публичным
- Проверить все ссылки перед коммитом

### Для Issue #5 (Exit Codes):
- Определить все места в коде, где возвращаются exit codes
- Убедиться, что каждый тип ошибки имеет правильный код
- Протестировать все сценарии для проверки корректности кодов
- Документировать exit codes в README с примерами использования

### Для Issue #6 (Quickstart):
- Сделать Quickstart максимально кратким и понятным
- Включить только самые необходимые шаги для начала работы
- Добавить ссылки на детальные разделы для более глубокого изучения
- Проверить, что все примеры кода работают корректно
