import sqlite3
import sys
import os

if len(sys.argv) < 2:
    print('Usage: python scripts/check_user_by_email.py user@example.com')
    sys.exit(2)

email = sys.argv[1].strip()
db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'ingat.db')
# normalize path
db_path = os.path.abspath(db_path)

if not os.path.exists(db_path):
    print('DB_NOT_FOUND', db_path)
    sys.exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('SELECT id, full_name, email, created_at FROM users WHERE email = ?', (email,))
rows = c.fetchall()
if not rows:
    print('NOT_FOUND')
else:
    for r in rows:
        # id, full_name, email, created_at
        print('FOUND', r[0], r[1], r[2], r[3])

conn.close()