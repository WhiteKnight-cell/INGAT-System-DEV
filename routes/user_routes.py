from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import re

user_bp = Blueprint('user', __name__, url_prefix='/user')


# ── Register ──
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


# ── User Login ──
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


# ── User Logout ──
@user_bp.route('/logout')
@login_required
def user_logout():
    logout_user()
    return redirect(url_for('user.user_login'))


# ── Forgot Password ──
from itsdangerous import URLSafeTimedSerializer
from flask import current_app


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


# ── Submit Complaint ──
@user_bp.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    if request.method == 'POST':
        violation_type = request.form.get('violation_type', '').strip()
        street_address = request.form.get('street_address', '').strip()
        barangay = request.form.get('barangay', '').strip()
        municipality = request.form.get('municipality', '').strip()
        date_incident = request.form.get('date_incident', '').strip()
        description = request.form.get('description', '').strip()
        photo = request.files.get('photo')

        if not violation_type:
            flash('Please select a violation type.', 'danger')
            return render_template('user/submit_complaint.html')

        if not street_address:
            flash('Please enter a street address.', 'danger')
            return render_template('user/submit_complaint.html')

        if not barangay:
            flash('Please enter a barangay.', 'danger')
            return render_template('user/submit_complaint.html')

        if not municipality:
            flash('Please enter a municipality.', 'danger')
            return render_template('user/submit_complaint.html')

        if not date_incident:
            flash('Please select the date of incident.', 'danger')
            return render_template('user/submit_complaint.html')

        if not description:
            flash('Please enter a description.', 'danger')
            return render_template('user/submit_complaint.html')

        if len(description) < 20:
            flash(f'Description must be at least 20 characters (you entered {len(description)}).', 'danger')
            return render_template('user/submit_complaint.html')

        allowed_types = ['Illegal Dumping', 'Air Pollution', 'Water Pollution', 'Illegal Logging', 'Others']
        if violation_type not in allowed_types:
            flash('Invalid violation type selected.', 'danger')
            return render_template('user/submit_complaint.html')

        from datetime import date
        try:
            incident_date = date.fromisoformat(date_incident)
            if incident_date > date.today():
                flash('Date of incident cannot be a future date.', 'danger')
                return render_template('user/submit_complaint.html')
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('user/submit_complaint.html')

        photo_path = None
        if photo and photo.filename != '':
            import os
            from werkzeug.utils import secure_filename
            from datetime import datetime as dt

            allowed_extensions = {'jpg', 'jpeg', 'png'}
            ext = photo.filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed_extensions:
                flash('Photo must be JPG or PNG only.', 'danger')
                return render_template('user/submit_complaint.html')

            photo.seek(0, 2)
            file_size = photo.tell()
            photo.seek(0)
            if file_size > 5 * 1024 * 1024:
                flash('Photo must not exceed 5MB.', 'danger')
                return render_template('user/submit_complaint.html')

            filename = secure_filename(photo.filename)
            unique_name = f'{current_user.id}_{dt.utcnow().strftime("%Y%m%d%H%M%S")}_{filename}'
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

        # Generate AI letter
        from utils import generate_complaint_letter
        letter = generate_complaint_letter(
            violation_type=violation_type,
            description=description,
            barangay=barangay,
            municipality=municipality,
            date_incident=date_incident,
            complainant_name=current_user.full_name,
            contact_number=current_user.contact_number,
            agency_name=agency_name
        )

        if letter:
            new_complaint.generated_letter = letter
            new_complaint.letter_generated = True
            db.session.commit()
            flash('Complaint submitted successfully!', 'success')
        else:
            flash('Complaint saved. Letter generation failed.', 'warning')

        return redirect(url_for('user.complaint_submitted', complaint_id=new_complaint.id))

    return render_template('user/submit_complaint.html')


# ── Complaint Submitted ──
@user_bp.route('/submitted/<int:complaint_id>')
@login_required
def complaint_submitted(complaint_id):
    from models import Complaint
    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('user.my_reports'))
    return render_template('user/complaint_submitted.html', complaint=complaint)


# ── My Reports ──
@user_bp.route('/my-reports')
@login_required
def my_reports():
    return render_template('user/my_reports.html')


# ── Download PDF
@user_bp.route('/submitted/<int:complaint_id>/download/pdf')
@login_required
def download_letter_pdf(complaint_id):
    from models import Complaint
    from fpdf import FPDF
    from flask import make_response

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('user.my_reports'))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Formal Complaint Letter', ln=True, align='C')

    pdf.set_font('Helvetica', size=11)
    pdf.cell(0, 8, f'Reference: #ING-{complaint.id:04d}', ln=True, align='C')
    pdf.ln(8)

    letter_text = complaint.generated_letter or 'No letter generated.'

    # Robust rendering to avoid FPDF multi_cell crashes
    for raw_line in letter_text.split('\n'):
        safe_line = (raw_line or '').encode('latin-1', 'replace').decode('latin-1')
        try:
            pdf.multi_cell(0, 7, safe_line)
        except Exception:
            for ch in safe_line:
                try:
                    pdf.cell(0, 7, ch, ln=1)
                except Exception:
                    pdf.cell(0, 7, '?', ln=1)

    pdf_bytes = pdf.output(dest='S')
    response = make_response(pdf_bytes.encode('latin-1') if isinstance(pdf_bytes, str) else pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=INGAT-Complaint-{complaint.id:04d}.pdf'
    return response


# ── Download DOCX ──
@user_bp.route('/submitted/<int:complaint_id>/download/docx')
@login_required
def download_letter_docx(complaint_id):
    from models import Complaint
    from docx import Document
    import io
    from flask import make_response

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('user.my_reports'))

    doc = Document()
    title = doc.add_heading('Formal Complaint Letter', 0)
    title.alignment = 1
    ref = doc.add_paragraph(f'Reference: #ING-{complaint.id:04d}')
    ref.alignment = 1
    doc.add_paragraph('')

    letter_text = complaint.generated_letter or 'No letter generated.'
    for line in letter_text.split('\n'):
        doc.add_paragraph(line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    response.headers['Content-Disposition'] = f'attachment; filename=INGAT-Complaint-{complaint.id:04d}.docx'
    return response

