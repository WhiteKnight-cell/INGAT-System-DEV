from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer
import re

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        barangay = request.form.get('barangay', '').strip()
        municipality = request.form.get('municipality', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not all([full_name, email, contact_number, barangay, municipality, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('user/register.html')

        if not contact_number.isdigit() or len(contact_number) != 11:
            flash('Contact number must be exactly 11 digits.', 'danger')
            return render_template('user/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('user/register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('user/register.html')

        if not re.search(r'[A-Z]', password):
            flash('Password must contain at least one uppercase letter.', 'danger')
            return render_template('user/register.html')

        if not re.search(r'[a-z]', password):
            flash('Password must contain at least one lowercase letter.', 'danger')
            return render_template('user/register.html')

        if not re.search(r'[0-9]', password):
            flash('Password must contain at least one number.', 'danger')
            return render_template('user/register.html')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must contain at least one special character.', 'danger')
            return render_template('user/register.html')

        from models import User
        from extensions import db
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return render_template('user/register.html')

        new_user = User(
            full_name=full_name,
            email=email,
            contact_number=contact_number,
            barangay=barangay,
            municipality=municipality,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('user.user_login'))

    return render_template('user/register.html')


@user_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('user/login.html')

        from models import User
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid credentials. Please try again.', 'danger')
            return render_template('user/login.html')

        if user.status == 'suspended':
            flash('Your account has been suspended. Please contact admin.', 'danger')
            return render_template('user/login.html')

        login_user(user)
        return redirect(url_for('user.submit_complaint'))

    return render_template('user/login.html')


@user_bp.route('/logout')
@login_required
def user_logout():
    logout_user()
    return redirect(url_for('user.user_login'))


@user_bp.route('/submit')
@login_required
def submit_complaint():
    return render_template('user/submit_complaint.html')

def generate_reset_token(email):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset-salt')


def verify_reset_token(token, expiration=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=expiration)
    except Exception:
        return None
    return email


@user_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('user/forgot_password.html')

        from models import User
        user = User.query.filter_by(email=email).first()

        if user:
            token = generate_reset_token(email)
            reset_url = url_for('user.reset_password', token=token, _external=True)
            body = f"""
            <h3>INGAT — Password Reset</h3>
            <p>Hello {user.full_name},</p>
            <p>Click the link below to reset your password:</p>
            <a href="{reset_url}" style="background:#2D6A4F;color:white;padding:10px 20px;
            border-radius:8px;text-decoration:none;">Reset Password</a>
            <p>This link expires in <strong>1 hour</strong>.</p>
            <p>If you did not request this, ignore this email.</p>
            """
            from utils import send_email
            send_email(email, 'INGAT — Password Reset Request', body)

        flash('If that email is registered, a reset link has been sent.', 'info')
        return redirect(url_for('user.forgot_password'))

    return render_template('user/forgot_password.html')


@user_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('user.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('user/reset_password.html', token=token)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('user/reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('user/reset_password.html', token=token)

        from models import User
        from extensions import db
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash('Password reset successfully! Please log in.', 'success')
            return redirect(url_for('user.user_login'))

    return render_template('user/reset_password.html', token=token)