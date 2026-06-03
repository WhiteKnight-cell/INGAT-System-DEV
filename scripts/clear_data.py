"""
Dangerous maintenance script — run only with a verified backup.
Deletes all regular `User` rows and all complaint/report data. Keeps `AdminUser` rows intact.
Usage: run from project root inside the venv:

    python scripts/clear_data.py

The script asks for interactive confirmation. It also offers to delete files in `static/uploads`.
"""
import os
import shutil
from pathlib import Path

from app import create_app
from extensions import db


def confirm(prompt: str) -> bool:
    r = input(prompt + "\nType DELETE to confirm: ")
    return r.strip() == 'DELETE'


def main():
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / 'ingat.db'
    print('Project root:', project_root)
    if db_path.exists():
        print('SQLite DB found at', db_path)
    else:
        print('No ingat.db found in project root. Ensure you are in the correct repo.')

    print('\n*** BACKUP WARNING ***')
    print('This will PERMANENTLY DELETE all regular user accounts, complaints, status history, and email verification records.')
    print('Admin users in the `admin_users` table will be kept intact.')
    if not confirm('Proceed with clearing user and report data?'):
        print('Aborting.')
        return

    delete_uploads = input('Also delete files in static/uploads? (y/N): ').strip().lower() == 'y'

    app = create_app()
    with app.app_context():
        from models import User, Complaint, EmailVerification, StatusHistory

        # Delete dependent records first
        print('Deleting status history...')
        StatusHistory.query.delete()
        print('Deleting complaints...')
        Complaint.query.delete()
        print('Deleting email verifications...')
        EmailVerification.query.delete()
        print('Deleting users...')
        User.query.delete()

        db.session.commit()
        print('Database rows removed. Committed.')

    if delete_uploads:
        uploads_dir = project_root / 'static' / 'uploads'
        if uploads_dir.exists() and uploads_dir.is_dir():
            print('Removing uploads in', uploads_dir)
            for p in uploads_dir.iterdir():
                try:
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        shutil.rmtree(p)
                except Exception as e:
                    print('Failed to remove', p, e)
            print('Uploads directory cleared.')
        else:
            print('No uploads directory found; skipping.')

    print('Done. All regular users and report data removed.')


if __name__ == '__main__':
    main()
