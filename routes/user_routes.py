from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user
import re

from routes.auth import member_required
from utils import generate_reset_token, send_email, verify_reset_token

user_bp = Blueprint('user', __name__, url_prefix='/user')

ALLOWED_VIOLATION_TYPES = [
    'Illegal Dumping',
    'Air Pollution',
    'Water Pollution',
    'Illegal Logging',
    'Others',
]


def _complaint_form_from_request():
    """Preserve submitted values when re-rendering the form after validation errors."""
    return {
        'violation_type': request.form.get('violation_type', '').strip(),
        'street_address': request.form.get('street_address', '').strip(),
        'barangay': request.form.get('barangay', '').strip(),
        'municipality': request.form.get('municipality', '').strip(),
        'date_incident': request.form.get('date_incident', '').strip(),
        'description': request.form.get('description', ''),
    }


def _render_submit_form(form=None):
    return render_template('user/submit_complaint.html', form=form or {})


def _register_form_from_request():
    """Preserve submitted values when re-rendering registration after validation errors."""
    return {
        'full_name': request.form.get('full_name', '').strip(),
        'email': request.form.get('email', '').strip(),
        'contact_number': request.form.get('contact_number', '').strip(),
        'barangay': request.form.get('barangay', '').strip(),
        'municipality': request.form.get('municipality', '').strip(),
        'password': request.form.get('password', ''),
        'confirm_password': request.form.get('confirm_password', ''),
    }


def _render_register_form(form=None):
    return render_template('user/register.html', form=form or {})


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form = _register_form_from_request()
        full_name = form['full_name']
        email = form['email']
        contact_number = form['contact_number']
        barangay = form['barangay']
        municipality = form['municipality']
        password = form['password'].strip()
        confirm_password = form['confirm_password'].strip()

        if not all([full_name, email, contact_number, barangay, municipality, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return _render_register_form(form)

        if not contact_number.isdigit() or len(contact_number) != 11:
            flash('Contact number must contain numbers only and be exactly 11 digits.', 'danger')
            return _render_register_form(form)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return _render_register_form(form)

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return _render_register_form(form)

        if not re.search(r'[A-Z]', password):
            flash('Password must contain at least one uppercase letter.', 'danger')
            return _render_register_form(form)

        if not re.search(r'[a-z]', password):
            flash('Password must contain at least one lowercase letter.', 'danger')
            return _render_register_form(form)

        if not re.search(r'[0-9]', password):
            flash('Password must contain at least one number.', 'danger')
            return _render_register_form(form)

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must contain at least one special character.', 'danger')
            return _render_register_form(form)

        from models import User
        from extensions import db
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return _render_register_form(form)

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

    return _render_register_form()


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
@member_required
def user_logout():
    logout_user()
    return redirect(url_for('user.user_login'))


@user_bp.route('/submit', methods=['GET', 'POST'])
@member_required
def submit_complaint():
    if request.method == 'POST':
        form = _complaint_form_from_request()
        violation_type = form['violation_type']
        street_address = form['street_address']
        barangay = form['barangay']
        municipality = form['municipality']
        date_incident = form['date_incident']
        description = form['description'].strip()
        photo = request.files.get('photo')

        if not violation_type:
            flash('Please select a violation type.', 'danger')
            return _render_submit_form(form)

        if not street_address:
            flash('Please enter a street address.', 'danger')
            return _render_submit_form(form)

        if not barangay:
            flash('Please enter a barangay.', 'danger')
            return _render_submit_form(form)

        if not municipality:
            flash('Please enter a municipality.', 'danger')
            return _render_submit_form(form)

        if not date_incident:
            flash('Please select the date of incident.', 'danger')
            return _render_submit_form(form)

        if not description:
            flash('Please enter a description of the violation.', 'danger')
            return _render_submit_form(form)

        if len(description) < 20:
            flash(
                f'Description must be at least 20 characters (you entered {len(description)}).',
                'danger',
            )
            return _render_submit_form(form)

        if violation_type not in ALLOWED_VIOLATION_TYPES:
            flash('Invalid violation type selected.', 'danger')
            return _render_submit_form(form)

        from datetime import date
        try:
            incident_date = date.fromisoformat(date_incident)
            if incident_date > date.today():
                flash('Date of incident cannot be a future date.', 'danger')
                return _render_submit_form(form)
        except ValueError:
            flash('Invalid date format.', 'danger')
            return _render_submit_form(form)

        photo_path = None
        if photo and photo.filename != '':
            import os
            from werkzeug.utils import secure_filename

            allowed_extensions = {'jpg', 'jpeg', 'png'}
            ext = photo.filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed_extensions:
                flash('Photo must be JPG or PNG only.', 'danger')
                return _render_submit_form(form)

            photo.seek(0, 2)
            file_size = photo.tell()
            photo.seek(0)
            if file_size > 5 * 1024 * 1024:
                flash('Photo must not exceed 5MB.', 'danger')
                return _render_submit_form(form)

            from datetime import datetime

            filename = secure_filename(photo.filename)
            unique_name = f'{current_user.id}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}_{filename}'
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            photo_path = os.path.join(upload_folder, unique_name)
            photo.save(photo_path)

        agency_map = {
            'Illegal Dumping': 'LGU',
            'Air Pollution': 'DENR',
            'Water Pollution': 'LLDA',
            'Illegal Logging': 'DENR',
            'Others': 'LGU'
        }
        agency_name = agency_map.get(violation_type, 'LGU')

        from models import Agency, Complaint
        from extensions import db

        agency = Agency.query.filter_by(agency_name=agency_name).first()
        agency_id = agency.id if agency else None

        new_complaint = Complaint(
            user_id=current_user.id,
            agency_id=agency_id,
            violation_type=violation_type,
            street_address=street_address,
            barangay=barangay,
            municipality=municipality,
            date_incident=incident_date,
            description=description,
            photo_path=photo_path,
            status='Submitted'
        )
        db.session.add(new_complaint)
        db.session.commit()

        letter_failed = False
        try:
            from services.gemini_letter import generate_complaint_letter

            letter_text = generate_complaint_letter(new_complaint, current_user, agency)
            new_complaint.generated_letter = letter_text
            new_complaint.letter_generated = True
            db.session.commit()
        except Exception as exc:
            letter_failed = True
            print(f'Gemini letter generation failed: {exc}')

        if letter_failed:
            flash(
                'Complaint saved successfully. Letter generation failed. Please try again later.',
                'warning',
            )
        else:
            flash('Complaint submitted successfully!', 'success')

        return redirect(url_for('user.complaint_submitted', complaint_id=new_complaint.id))

    return _render_submit_form()


@user_bp.route('/submitted/<int:complaint_id>')
@member_required
def complaint_submitted(complaint_id):
    from models import Complaint

    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id:
        abort(403)
    return render_template('user/complaint_submitted.html', complaint=complaint)


def _get_owned_complaint_with_letter(complaint_id):
    from models import Complaint

    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id:
        abort(403)
    if not complaint.letter_generated or not complaint.generated_letter:
        flash('No generated letter is available for this complaint.', 'warning')
        return None
    return complaint


@user_bp.route('/submitted/<int:complaint_id>/download/pdf')
@member_required
def download_letter_pdf(complaint_id):
    complaint = _get_owned_complaint_with_letter(complaint_id)
    if not complaint:
        return redirect(url_for('user.complaint_submitted', complaint_id=complaint_id))

    from services.letter_export import build_letter_pdf

    pdf_buffer = build_letter_pdf(complaint.generated_letter, complaint.id)
    filename = f'INGAT_Complaint_{complaint.id:04d}.pdf'
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@user_bp.route('/submitted/<int:complaint_id>/download/docx')
@member_required
def download_letter_docx(complaint_id):
    complaint = _get_owned_complaint_with_letter(complaint_id)
    if not complaint:
        return redirect(url_for('user.complaint_submitted', complaint_id=complaint_id))

    from services.letter_export import build_letter_docx

    docx_buffer = build_letter_docx(complaint.generated_letter, complaint.id)
    filename = f'INGAT_Complaint_{complaint.id:04d}.docx'
    return send_file(
        docx_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=filename,
    )


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


@user_bp.route('/my-reports')
@member_required
def my_reports():
    return render_template('user/my_reports.html')
