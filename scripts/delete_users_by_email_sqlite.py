"""Delete one or more users (and dependent rows) by email from the INGAT SQLite DB.

Usage:
  python scripts/delete_users_by_email_sqlite.py email1@example.com email2@example.com ...

This script deletes:
- status_history rows linked to the user's complaints
- complaints rows for the user
- email_verifications rows for the user
- users row

Notes:
- Script uses direct sqlite3 and is meant for maintenance/testing.
- You should backup ingat.db before running.
"""

import os
import sys
import sqlite3
from typing import List


def get_db_path() -> str:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(project_root, 'instance', 'ingat.db')
    return db_path


def delete_user_by_email(conn: sqlite3.Connection, email: str) -> None:
    c = conn.cursor()

    c.execute(
        'SELECT id, full_name, email, created_at FROM users WHERE email = ?',
        (email,),
    )
    row = c.fetchone()
    if not row:
        print('User not found:', email)
        return

    user_id = row[0]
    print('Found user:', user_id, row[2])

    # Complaint ids
    c.execute('SELECT id FROM complaints WHERE user_id = ?', (user_id,))
    complaint_rows = c.fetchall()
    complaint_ids = [r[0] for r in complaint_rows]

    deleted_status = 0
    if complaint_ids:
        placeholders = ','.join(['?'] * len(complaint_ids))
        c.execute(
            f'DELETE FROM status_history WHERE complaint_id IN ({placeholders})',
            complaint_ids,
        )
        deleted_status = c.rowcount

    c.execute('DELETE FROM complaints WHERE user_id = ?', (user_id,))
    deleted_complaints = c.rowcount

    # Table name in this DB is `email_verifications`? If not present, skip.
    deleted_verifs = 0
    try:
        c.execute('DELETE FROM email_verifications WHERE user_id = ?', (user_id,))
        deleted_verifs = c.rowcount
    except sqlite3.OperationalError:
        deleted_verifs = 0


    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    deleted_users = c.rowcount

    print('Deleted:', deleted_status, 'status history rows')
    print('Deleted:', deleted_complaints, 'complaint rows')
    print('Deleted:', deleted_verifs, 'email verification rows')
    print('Deleted:', deleted_users, 'user rows')
    print('User removed:', email)


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print('Usage: python scripts/delete_users_by_email_sqlite.py email1 email2 ...')
        return 2

    db_path = get_db_path()
    if not os.path.exists(db_path):
        print('DB_NOT_FOUND', db_path)
        return 1

    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        for email in argv[1:]:
            email = email.strip()
            if email:
                delete_user_by_email(conn, email)
        conn.commit()
    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

