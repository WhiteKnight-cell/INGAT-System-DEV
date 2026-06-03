"""
Delete a user and related data by email. Use with PYTHONPATH set to project root.
Usage:
  python scripts/delete_user_by_email.py user@example.com
This deletes EmailVerification, StatusHistory, Complaint rows for that user, then the User.
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Usage: python scripts/delete_user_by_email.py user@example.com')
    sys.exit(1)

email = sys.argv[1].strip()

# import app context
from app import create_app
from extensions import db

app = create_app()
with app.app_context():
    from models import User, Complaint, EmailVerification, StatusHistory

    user = User.query.filter_by(email=email).first()
    if not user:
        print('User not found:', email)
        sys.exit(0)

    print('Found user:', user.id, user.email)

    # delete status history for user's complaints
    complaints = Complaint.query.filter_by(user_id=user.id).all()
    for c in complaints:
        deleted_sh = StatusHistory.query.filter_by(complaint_id=c.id).delete()
    # delete complaints
    deleted_complaints = Complaint.query.filter_by(user_id=user.id).delete()
    # delete email verifications
    deleted_verifs = EmailVerification.query.filter_by(user_id=user.id).delete()
    # finally delete user
    db.session.delete(user)
    db.session.commit()

    print('Deleted:', deleted_sh if 'deleted_sh' in locals() else 0, 'status history rows (last checked)')
    print('Deleted:', deleted_complaints, 'complaint rows')
    print('Deleted:', deleted_verifs, 'email verification rows')
    print('User removed:', email)
