from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user

from routes.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('admin/login.html')

        from models import AdminUser
        admin = AdminUser.query.filter_by(email=email).first()

        if not admin or not check_password_hash(admin.password_hash, password):
            flash('Invalid credentials. Please try again.', 'danger')
            return render_template('admin/login.html')

        login_user(admin)
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/login.html')


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    from models import Complaint
    total = Complaint.query.count()
    pending = Complaint.query.filter_by(status='Submitted').count()
    forwarded = Complaint.query.filter_by(status='Forwarded to Agency').count()
    resolved = Complaint.query.filter_by(status='Resolved').count()
    recent_complaints = Complaint.query.order_by(
        Complaint.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html',
                           total=total,
                           pending=pending,
                           forwarded=forwarded,
                           resolved=resolved,
                           recent_complaints=recent_complaints)


@admin_bp.route('/logout')
@admin_required
def logout():
    logout_user()
    return redirect(url_for('admin.admin_login'))