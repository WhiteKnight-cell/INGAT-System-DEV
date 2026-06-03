import sqlite3
import sys
import os

if len(sys.argv) < 2:
    print('Usage: python scripts/delete_user_by_email_sqlite.py user@example.com')
    sys.exit(2)

email = sys.argv[1].strip()
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
db_path = os.path.join(project_root, 'instance', 'ingat.db')

if not os.path.exists(db_path):
    print('DB_NOT_FOUND', db_path)
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT id, full_name, email, created_at FROM users WHERE email = ?', (email,))
user = c.fetchone()
if not user:
    print('User not found:', email)
    conn.close()
    sys.exit(0)

user_id = user['id']
print('Found user:', user_id, user['email'])

# collect complaint ids
c.execute('SELECT id FROM complaints WHERE user_id = ?', (user_id,))
complaints = [row['id'] for row in c.fetchall()]

deleted_status = 0
if complaints:
    placeholders = ','.join(['?'] * len(complaints))
    c.execute(f'DELETE FROM status_history WHERE complaint_id IN ({placeholders})', complaints)
    deleted_status = c.rowcount

# delete complaints
c.execute('DELETE FROM complaints WHERE user_id = ?', (user_id,))
deleted_complaints = c.rowcount

# delete email verifications
c.execute('DELETE FROM email_verifications WHERE user_id = ?', (user_id,))
deleted_verifs = c.rowcount

# delete user
c.execute('DELETE FROM users WHERE id = ?', (user_id,))
deleted_users = c.rowcount

conn.commit()
print('Deleted:', deleted_status, 'status history rows')
print('Deleted:', deleted_complaints, 'complaint rows')
print('Deleted:', deleted_verifs, 'email verification rows')
print('Deleted:', deleted_users, 'user rows')
print('User removed:', email)

conn.close()