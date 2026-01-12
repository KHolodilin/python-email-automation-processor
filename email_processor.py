#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMAIL PROCESSOR — v7 (YAML + keyring + per-day UID storage)

Скрипт загружает вложения из IMAP-почты, раскладывает их по каталогам,
архивирует письма, хранит обработанные UID по дням (processed_uids/YYYY-MM-DD.txt)
и использует быстрый двухфазный FETCH.

Python 3.8+
Зависимости: pyyaml, keyring
"""
import argparse
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Set, Dict
import time
import getpass

import yaml
import keyring

# ==============================
# КОНСТАНТЫ
# ==============================

KEYRING_SERVICE_NAME = "email-vkh-processor"
CONFIG_FILE = "config.yaml"


# ==============================
# ЛОГИРОВАНИЕ
# ==============================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


# ==============================
# ЗАГРУЗКА КОНФИГА
# ==============================

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Не найден файл конфигурации: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("config.yaml должен содержать YAML-объект верхнего уровня.")
    return cfg


# ==============================
# ПАРОЛЬ IMAP (KEYRING + FALLBACK)
# ==============================

def get_imap_password(imap_user: str) -> str:
    password = keyring.get_password(KEYRING_SERVICE_NAME, imap_user)
    if password:
        logging.info(
            "Пароль для %s получен из keyring (%s).",
            imap_user,
            KEYRING_SERVICE_NAME,
        )
        return password

    logging.info(
        "Пароль для %s не найден в keyring. Запрос через консоль.", imap_user
    )
    pw = getpass.getpass(f"Введите пароль IMAP для {imap_user}: ")
    if not pw:
        raise ValueError("Пароль не введён, работа прервана.")

    answer = input("Сохранить пароль в системном хранилище (keyring)? [y/N]: ").strip().lower()
    if answer == "y":
        try:
            keyring.set_password(KEYRING_SERVICE_NAME, imap_user, pw)
            logging.info("Пароль сохранён в keyring (%s).", KEYRING_SERVICE_NAME)
        except Exception as e:
            logging.error("Не удалось сохранить пароль в keyring: %s", e)

    return pw


# ==============================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================

def get_start_date(days_back: int) -> str:
    date_from = datetime.now() - timedelta(days=days_back)
    return date_from.strftime("%d-%b-%Y")


def normalize_folder_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    return name[:200]


def decode_mime_header_value(value: Optional[str]) -> str:
    if not value:
        return ""
    decoded = decode_header(value)
    result = ""
    for part, charset in decoded:
        if charset:
            result += part.decode(charset, errors="replace")
        else:
            result += part if isinstance(part, str) else part.decode(errors="replace")
    return result


def resolve_custom_folder(subject: str, topic_mapping: dict) -> Optional[str]:
    for pattern, folder in topic_mapping.items():
        if re.search(pattern, subject, flags=re.IGNORECASE):
            logging.info(
                "Тема '%s' совпала с шаблоном '%s' → папка %s",
                subject,
                pattern,
                folder,
            )
            return folder
    return None


def safe_save_path(folder: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(folder, filename)
    counter = 1

    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{base}_{counter:02d}{ext}")
        counter += 1

    return candidate


def parse_email_date(date_raw: str) -> Optional[datetime]:
    if not date_raw:
        return None
    try:
        dt = parsedate_to_datetime(date_raw)
        if dt is None:
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return None


# ==============================
# ХРАНИЛИЩЕ UID ПО ДНЯМ
# ==============================

def ensure_processed_dir(root_dir: str) -> None:
    os.makedirs(root_dir, exist_ok=True)


def get_processed_file_path(root_dir: str, day_str: str) -> str:
    ensure_processed_dir(root_dir)
    filename = f"{day_str}.txt"
    return os.path.join(root_dir, filename)


def load_processed_for_day(root_dir: str, day_str: str, cache: Dict[str, Set[str]]) -> Set[str]:
    if day_str in cache:
        return cache[day_str]

    path = get_processed_file_path(root_dir, day_str)
    if not os.path.exists(path):
        cache[day_str] = set()
        return cache[day_str]

    with open(path, "r", encoding="utf-8") as f:
        uids = {line.strip() for line in f if line.strip()}

    cache[day_str] = uids
    logging.debug("Загружено %s UID из %s", len(uids), path)
    return cache[day_str]


def save_processed_uid_for_day(root_dir: str, day_str: str, uid: str, cache: Dict[str, Set[str]]) -> None:
    uids = load_processed_for_day(root_dir, day_str, cache)
    if uid in uids:
        return

    path = get_processed_file_path(root_dir, day_str)
    with open(path, "a", encoding="utf-8") as f:
        f.write(uid + "\n")
    uids.add(uid)
    logging.debug("UID=%s добавлен в %s", uid, path)


def cleanup_old_processed_days(root_dir: str, keep_days: int) -> None:
    if keep_days <= 0:
        return

    ensure_processed_dir(root_dir)
    cutoff = datetime.now().date() - timedelta(days=keep_days)

    for name in os.listdir(root_dir):
        path = os.path.join(root_dir, name)
        if not os.path.isfile(path):
            continue
        base, ext = os.path.splitext(name)
        if ext != ".txt":
            continue
        try:
            day = datetime.strptime(base, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            try:
                os.remove(path)
                logging.info("Удалён устаревший processed UID файл: %s", path)
            except Exception as e:
                logging.error("Не удалось удалить %s: %s", path, e)


# ==============================
# IMAP
# ==============================

def imap_connect(server: str, user: str, password: str, max_retries: int, retry_delay: int):
    attempts = 0
    while attempts < max_retries:
        try:
            attempts += 1
            logging.info("IMAP: подключение к %s (попытка %s/%s)...", server, attempts, max_retries)
            mail = imaplib.IMAP4_SSL(server)
            mail.login(user, password)
            logging.info("IMAP: успешное подключение.")
            return mail
        except Exception as e:
            logging.error("Ошибка IMAP-подключения: %s", e)
            if attempts < max_retries:
                logging.info("Повторная попытка через %s сек...", retry_delay)
                time.sleep(retry_delay)
    raise ConnectionError("IMAP: не удалось подключиться после всех попыток.")


def archive_message(mail, uid: str, archive_folder: str) -> None:
    try:
        mail.create(archive_folder)
    except Exception:
        pass

    result = mail.uid("COPY", uid, archive_folder)
    if not result or result[0] != "OK":
        logging.error("COPY: не удалось переместить UID=%s → %s", uid, archive_folder)
        return

    mail.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
    mail.expunge()
    logging.info("Письмо UID=%s архивировано → %s", uid, archive_folder)


# ==============================
# ОСНОВНОЙ ПРОЦЕССОР
# ==============================

def download_attachments(config: dict) -> None:
    # --- Конфиг ---
    imap_cfg = config.get("imap", {})
    proc_cfg = config.get("processing", {})
    allowed_senders = config.get("allowed_senders", [])
    topic_mapping = config.get("topic_mapping", {})

    imap_server = imap_cfg.get("server")
    imap_user = imap_cfg.get("user")

    max_retries = int(imap_cfg.get("max_retries", 5))
    retry_delay = int(imap_cfg.get("retry_delay", 3))

    start_days_back = int(proc_cfg.get("start_days_back", 5))
    download_dir = proc_cfg.get("download_dir", "downloads")
    archive_folder = proc_cfg.get("archive_folder", "INBOX/Processed")
    processed_dir = proc_cfg.get("processed_dir", "processed_uids")
    keep_processed_days = int(proc_cfg.get("keep_processed_days", 0))

    archive_only_mapped = bool(proc_cfg.get("archive_only_mapped", True))
    skip_non_allowed_as_processed = bool(proc_cfg.get("skip_non_allowed_as_processed", True))
    skip_unmapped_as_processed = bool(proc_cfg.get("skip_unmapped_as_processed", True))

    cleanup_old_processed_days(processed_dir, keep_processed_days)

    # Пароль IMAP
    imap_password = get_imap_password(imap_user)

    start_date = get_start_date(start_days_back)
    logging.info("Начало обработки. Письма с: %s", start_date)

    processed_cache: Dict[str, Set[str]] = {}

    mail = None
    try:
        mail = imap_connect(imap_server, imap_user, imap_password, max_retries, retry_delay)

        status, _ = mail.select("INBOX")
        if status != "OK":
            logging.error("Не удалось выбрать INBOX.")
            return

        status, messages = mail.search(None, f'(SINCE "{start_date}")')
        if status != "OK":
            logging.error("Ошибка поиска писем")
            return

        email_ids = messages[0].split() if messages and messages[0] else []
        logging.info("Найдено писем: %s", len(email_ids))

        allowed_lower = {s.lower() for s in allowed_senders}

        for msg_id in reversed(email_ids):
            try:
                # --- FETCH UID ---
                status, meta = mail.fetch(msg_id, "(UID RFC822.SIZE BODYSTRUCTURE)")
                if status != "OK" or not meta or not meta[0]:
                    continue

                raw = meta[0][0].decode("utf-8", errors="ignore") if isinstance(meta[0], tuple) else meta[0].decode("utf-8", errors="ignore")
                uid_match = re.search(r"UID (\d+)", raw)
                uid = uid_match.group(1) if uid_match else None
                if not uid:
                    continue

                # --- FETCH HEADER (FROM SUBJECT DATE) ---
                status, header_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if status != "OK" or not header_data or not header_data[0]:
                    continue

                header_bytes = header_data[0][1] if isinstance(header_data[0], tuple) else header_data[0]
                header_msg = email.message_from_bytes(header_bytes)

                sender = email.utils.parseaddr(header_msg.get("From", ""))[1]
                subject = decode_mime_header_value(header_msg.get("Subject", "(без темы)"))
                date_raw = header_msg.get("Date", "")
                dt = parse_email_date(date_raw)
                day_str = dt.strftime("%Y-%m-%d") if dt else "nodate"

                processed_for_day = load_processed_for_day(processed_dir, day_str, processed_cache)
                if uid in processed_for_day:
                    continue

                # --- фильтр отправителей ---
                if sender.lower() not in allowed_lower:
                    logging.debug("UID=%s: отправитель %s не разрешён", uid, sender)
                    if skip_non_allowed_as_processed:
                        save_processed_uid_for_day(processed_dir, day_str, uid, processed_cache)
                    continue

                # --- определение папки ---
                mapped_folder = resolve_custom_folder(subject, topic_mapping)
                if mapped_folder:
                    target_folder = os.path.join(download_dir, mapped_folder)
                else:
                    target_folder = os.path.join(download_dir, normalize_folder_name(subject))
                os.makedirs(target_folder, exist_ok=True)

                # --- Полное письмо ---
                status, full_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK" or not full_data or not full_data[0]:
                    save_processed_uid_for_day(processed_dir, day_str, uid, processed_cache)
                    continue

                msg_bytes = full_data[0][1] if isinstance(full_data[0], tuple) else full_data[0]
                msg = email.message_from_bytes(msg_bytes)

                attachments_found = False
                for part in msg.walk():
                    if part.get_content_disposition() == "attachment":
                        filename_raw = part.get_filename()
                        filename = decode_mime_header_value(filename_raw)
                        if not filename:
                            continue
                        save_path = safe_save_path(target_folder, filename)
                        with open(save_path, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        attachments_found = True
                        logging.info("UID=%s: сохранён файл %s", uid, save_path)

                # --- Обработка завершена ---
                save_processed_uid_for_day(processed_dir, day_str, uid, processed_cache)

                # --- Архивация ---
                if mapped_folder and archive_only_mapped:
                    archive_message(mail, uid, archive_folder)
                else:
                    if skip_unmapped_as_processed:
                        pass

            except Exception as e:
                logging.exception("Ошибка обработки письма id=%s: %s", msg_id, e)

    finally:
        if mail:
            try:
                mail.logout()
            except:
                pass
        logging.info("Скрипт завершён.")

def clear_passwords(service: str, primary_user: str):
    print(f"\nОчистка паролей для сервиса: {service}")
    confirm = input("Вы действительно хотите удалить все сохранённые пароли? [y/N]: ").strip().lower()

    if confirm != "y":
        print("Отменено.")
        return

    deleted = 0

    # Основной пользователь из config.yaml
    try:
        keyring.delete_password(service, primary_user)
        print(f"Удалено: {service} / {primary_user}")
        deleted += 1
    except Exception:
        print(f"Не найдено: {service} / {primary_user}")

    # Можем также удалить fallback-логины, если появятся
    possible_users = [
        primary_user,
        primary_user.lower(),
        primary_user.upper(),
    ]

    for user in set(possible_users):
        try:
            keyring.delete_password(service, user)
            print(f"Удалено: {service} / {user}")
            deleted += 1
        except Exception:
            pass

    print(f"\nГотово. Удалено записей: {deleted}")


# В main:
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear-passwords", action="store_true", help="Очистить сохранённые пароли keyring")
    args = parser.parse_args()

    cfg = load_config(CONFIG_FILE)

    if args.clear_passwords:
        user = cfg.get("imap", {}).get("user")
        if not user:
            raise ValueError("В config.yaml отсутствует imap.user")
        clear_passwords(KEYRING_SERVICE_NAME, user)
    else:
        download_attachments(cfg)