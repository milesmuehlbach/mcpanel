from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3

from app.downloaders import java, server
from app.paths import get_workdir


def _normalize_permissions(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str):
            continue

        permission = item.strip()
        if not permission or permission in seen:
            continue

        seen.add(permission)
        normalized.append(permission)

    return normalized


def get_db() -> sqlite3.Connection:
    db_path = get_workdir() / "default.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db() -> None:
    with get_db() as db:
        db.execute("PRAGMA journal_mode=WAL;")
        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY NOT NULL,
                value TEXT NOT NULL
            );
            """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_argon2 TEXT NOT NULL,
                permissions TEXT NOT NULL
            );
            """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS components (
                uid TEXT PRIMARY KEY NOT NULL,
                installed_at TIMESTAMP NOT NULL
            );
            """)


def get_setting(key: str, value: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is not None:
            return row[0]

        db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise RuntimeError(f"failed to init setting: {key}")

        return row[0]


def get_user_login_record(username: str) -> tuple[int, str] | None:
    with get_db() as db:
        row = db.execute(
            "SELECT id, password_argon2 FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return None

    return row[0], row[1]


def get_username(uid: int) -> str | None:
    with get_db() as db:
        row = db.execute(
            "SELECT username FROM users WHERE id = ?",
            (uid,),
        ).fetchone()

    if row is None:
        return None

    return row[0]


def get_user_count() -> int:
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) FROM users").fetchone()

    if row is None:
        raise RuntimeError("failed to query user count")

    return row[0]


def create_user(username: str, password_hash: str, permissions: list[str]) -> None:
    with get_db() as db:
        db.execute(
            "INSERT INTO users (username, password_argon2, permissions) VALUES (?, ?, ?)",
            (
                username,
                password_hash,
                json.dumps(permissions),
            ),
        )


def get_user_permissions(uid: int) -> list[str] | None:
    with get_db() as db:
        row = db.execute(
            "SELECT permissions FROM users WHERE id = ?",
            (uid,),
        ).fetchone()

    if row is None:
        return None

    permissions = row[0]

    try:
        parsed = json.loads(permissions)
        normalized = _normalize_permissions(parsed)
    except json.JSONDecodeError:
        normalized = []

    if permissions != json.dumps(normalized):
        set_user_permissions(uid, normalized)

    return normalized


def set_user_permissions(uid: int, permissions: list[str]) -> None:
    with get_db() as db:
        db.execute(
            "UPDATE users SET permissions = ? WHERE id = ?",
            (json.dumps(permissions), uid),
        )


def update_component_database(uid: str) -> None:
    with get_db() as db:
        db.execute(
            """
            INSERT INTO components (uid, installed_at)
            VALUES (?, ?)
            ON CONFLICT(uid) DO UPDATE SET installed_at = excluded.installed_at
            """,
            (uid, datetime.now()),
        )


def remove_component_database(uid: str) -> None:
    with get_db() as db:
        db.execute(
            "DELETE FROM components WHERE uid = ?",
            (uid,),
        )


def get_installed_components() -> dict[str, str]:
    with get_db() as db:
        rows = db.execute("SELECT uid, installed_at FROM components").fetchall()

    return dict(rows)


def install_jre_component(uid: str, sha256: str, workdir: Path) -> None:
    java.download_runtime(uid, sha256, workdir)
    update_component_database(uid)


def install_server_component(uid: str, hash: str | None, workdir: Path) -> None:
    server.download_version(uid, hash, workdir)
    update_component_database(uid)
