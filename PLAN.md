# Project Improvement Plan

## Plan Structure
Each task includes:
1. Create GitHub Issue
2. Create branch `feature/issue-{number}-{name}`
3. **Switch to new branch** (manually): `git checkout -b feature/issue-{number}-{name}`
4. Implement changes
5. Testing and verification
6. Commit changes
7. **Bump version** in `pyproject.toml` before creating PR (patch version: 7.4.X → 7.4.X+1)
8. **Push branch** (manually): `git push origin feature/issue-{number}-{name}`
9. **Create Pull Request** with `main`/`master` branch

---

## Issue #1: Codecov Integration

**Title (EN):** Integrate Codecov for coverage reporting

**Description (EN):** Improve Codecov integration in CI/CD pipeline. Currently, Codecov action is present but may not be fully configured. Enhance the integration to ensure proper coverage reporting, add coverage thresholds, and configure Codecov settings for better visibility and reporting.

### Branch: `feature/issue-1-integrate-codecov`

### Tasks:
- [ ] Improve Codecov configuration in CI workflow
  - Verify correct generation of `coverage.xml`
  - Add `--cov-report=xml` flag to pytest for XML report generation
  - Configure correct parameters for codecov-action
  - Add Codecov token (if required)
- [ ] Add Codecov configuration
  - Create `codecov.yml` to configure Codecov behavior
  - Set minimum coverage threshold
  - Configure coverage drop notifications
- [ ] Add coverage check in CI
  - Add `--cov-fail-under` for minimum coverage check
  - Configure fail when coverage drops below threshold
- [ ] Update documentation
  - Add Codecov information to README
  - Add link to Codecov dashboard

### After completion:
```bash
# Testing and verification
pytest --cov=email_processor --cov-report=xml --cov-report=term-missing
# Verify that coverage.xml is created
# Verify that Codecov receives data

# Commit
git add .
git commit -m "ci: integrate Codecov for coverage reporting

Fixes #1"

# Push and create PR (manually)
git push origin feature/issue-1-integrate-codecov
# Then create Pull Request via GitHub UI or CLI
```

---

## Issue #2: Improve Test Coverage to 95%

**Title (EN):** Improve test coverage to 95%+

**Description (EN):** Increase test coverage from current level to at least 95% by adding comprehensive tests for all modules. This will improve code reliability, maintainability, and ensure better code quality through extensive testing.

### Branch: `feature/issue-2-improve-test-coverage-95`

### Tasks:
- [ ] Analyze current coverage
  - Run `pytest --cov=email_processor --cov-report=term-missing`
  - Identify modules with low coverage
  - Create list of missing tests
- [ ] Add tests for modules with low coverage
  - Tests for all public methods and classes
  - Tests for edge cases and boundary conditions
  - Tests for error handling
  - Tests for all code branches (if/else, try/except)
- [ ] Add integration tests
  - Tests for full processing cycle
  - Tests for module interactions
  - Tests for real-world usage scenarios
- [ ] Configure coverage check in CI
  - Add `--cov-fail-under=95` to pytest command
  - Ensure CI fails when coverage drops below 95%
- [ ] Update testing documentation
  - Update `README_TESTS.md` with coverage information
  - Add instructions for running tests with coverage

### Coverage Goal: ≥95%

### After completion:
```bash
# Тестирование и проверки
pytest --cov=email_processor --cov-report=term-missing --cov-fail-under=95
pre-commit run --all-files
python -m email_processor --version  # Verify functionality

# Commit
git add .
git commit -m "test: improve test coverage to 95%+

Fixes #2"

# Push и создание PR (вручную)
git push origin feature/issue-2-improve-test-coverage-95
# Затем создать Pull Request через GitHub UI или CLI
```

---

## Issue #3: Add Project Documentation (Code of Conduct, License, Security Policy, Templates)

**Title (EN):** Add project documentation and templates (Code of Conduct, License, Security Policy, Issue/PR templates)

**Description (EN):** Add essential project documentation files including Code of Conduct, License file, Security Policy, and GitHub templates for issues and pull requests. This will improve project professionalism, provide clear guidelines for contributors, and streamline the contribution process.

### Branch: `feature/issue-3-add-project-documentation`

### Tasks:
- [ ] Add LICENSE file
  - Choose license (MIT, Apache 2.0, or other)
  - Create `LICENSE` file with full license text
  - Update `pyproject.toml` if needed (MIT already specified)
- [ ] Add CODE_OF_CONDUCT.md
  - Use Contributor Covenant or create custom one
  - Add information on how to report violations
  - Add contact information
- [ ] Add SECURITY.md (Security Policy)
  - Describe vulnerability reporting process
  - Specify supported versions
  - Add information on fix process
  - Create in `.github/SECURITY.md` or project root
- [ ] Create Issue templates
  - Create `.github/ISSUE_TEMPLATE/` directory
  - Add template for bug reports (`bug_report.md`)
  - Add template for feature requests (`feature_request.md`)
  - Add template for questions (`question.md`) - optional
  - Configure `config.yml` for template selection
- [ ] Create Pull Request template
  - Create `.github/pull_request_template.md`
  - Add sections: description, change type, checks, related issues
  - Add checklist for pre-PR verification

### After completion:
```bash
# File verification
# Ensure all files are created and correct
# Check Markdown formatting

# Commit
git add .
git commit -m "docs: add Code of Conduct, License, Security Policy, and templates

- Add LICENSE file
- Add CODE_OF_CONDUCT.md
- Add SECURITY.md
- Add GitHub issue templates
- Add pull request template

Fixes #3"

# Push and create PR (manually)
git push origin feature/issue-3-add-project-documentation
# Then create Pull Request via GitHub UI or CLI
```

---

## Issue #4: Добавление бейджей в README

**Title (EN):** Add project badges to README

**Description (EN):** Add professional project badges to README.md to display project status, version, test coverage, CI status, and other important metrics. This will improve project visibility and provide quick access to key project information.

### Ветка: `feature/issue-4-add-readme-badges`

### Задачи:
- [ ] Добавить бейджи в начало README.md
  - PyPI version badge: `[![PyPI](https://img.shields.io/pypi/v/email-processor)](https://pypi.org/project/email-processor/)`
  - CI status badge: `[![CI](https://github.com/KHolodilin/python-email-automation-processor/actions/workflows/ci.yml/badge.svg)](https://github.com/KHolodilin/python-email-automation-processor/actions/workflows/ci.yml)`
  - Test Coverage badge: `[![Test Coverage](https://codecov.io/gh/KHolodilin/python-email-automation-processor/branch/main/graph/badge.svg)](https://codecov.io/gh/KHolodilin/python-email-automation-processor)`
  - Python version badge: `[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)`
  - License badge: `[![License](https://img.shields.io/github/license/KHolodilin/python-email-automation-processor)](LICENSE)`
  - Stars badge: `[![Stars](https://img.shields.io/github/stars/KHolodilin/python-email-automation-processor)](https://github.com/KHolodilin/python-email-automation-processor/stargazers)`
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
