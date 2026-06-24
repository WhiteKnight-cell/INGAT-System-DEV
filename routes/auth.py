from functools import wraps

from flask import flash, redirect, url_for, session
from flask_login import current_user, login_required


def admin_required(fn):
    @login_required
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from models import AdminUser

        if not isinstance(current_user, AdminUser):
            flash('Please log in as admin.', 'danger')
            return redirect(url_for('admin.admin_login'))

        if session.get('_admin_st') != current_user.session_token:
            from flask_login import logout_user
            logout_user()
            session.pop('_admin_st', None)
            flash('Session expired. Please log in again.', 'danger')
            return redirect(url_for('admin.admin_login'))

        return fn(*args, **kwargs)

    return wrapper


def member_required(fn):
    @login_required
    @wraps(fn)
    def wrapper(*args, **kwargs):

        from models import AdminUser, User

        if isinstance(current_user, AdminUser):
            flash('You are logged in as an admin. Log out first to access user pages.', 'warning')
            return redirect(url_for('admin.dashboard'))
        if not isinstance(current_user, User):
            flash('Please log in to continue.', 'danger')
            return redirect(url_for('user.user_login'))
        return fn(*args, **kwargs)

    return wrapper
