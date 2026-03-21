import sqlite3
import os


def test_db():
    db_path = "database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)"
    )

    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("test_user", "test_pass"),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass

    cursor.execute("SELECT * FROM users WHERE username=?", ("test_user",))
    user = cursor.fetchone()
    conn.close()

    if user:
        print("Success")
    else:
        print("Failure")


if __name__ == "__main__":
    test_db()
