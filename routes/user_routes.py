from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file, session
from utils import hash_password, verify_password, is_bcrypt_hash
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta
import re

from routes.auth import member_required
from utils import (
    generate_reset_token,
    send_email,
    verify_reset_token,
    generate_otp_code,
    send_verification_email,
)

from werkzeug.utils import secure_filename
import os
from datetime import date

from extensions import db
from models import User, Agency, Complaint

user_bp = Blueprint('user', __name__, url_prefix='/user')

# seconds to wait before allowing resend
RESEND_COOLDOWN_SECONDS = 60

ALLOWED_VIOLATION_TYPES = [
    'Illegal Dumping',
    'Air Pollution',
    'Water Pollution',
    'Toxic Waste',
    'Illegal Fishing',
    'Marine Habitat Destruction',
    'Poaching',
    'Illegal Logging',
    'Unauthorized Timber Transport',
    'Kaingin',
    'Industrial Water Pollution',
    'Illegal Reclamation',
    'Others',
]


def _password_error(password):
    if len(password) < 8:
        return 'Password must be at least 8 characters.'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return 'Password must contain at least one lowercase letter.'
    if not re.search(r'[0-9]', password):
        return 'Password must contain at least one number.'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return 'Password must contain at least one special character.'
    return None


def _create_email_verification(user):
    from extensions import db
    from models import EmailVerification

    otp_code = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    verification = EmailVerification(
        user_id=user.id,
        otp_code=otp_code,
        expires_at=expires_at,
    )
    db.session.add(verification)
    db.session.commit()
    return verification


def _send_account_verification_email(user, otp_code):
    sent = send_verification_email(user.email, user.full_name, otp_code)
    if not sent:
        print(f'Failed to send verification email for user {user.email}')
        print(f'Local OTP for {user.email}: {otp_code}')
    return sent


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
    return render_template('user/register.html', form=form or {}, f=form or {})


def _generate_letter_for_complaint(complaint, complainant):
    """Generate and persist Gemini letter. Returns (success, user_message_or_none)."""
    from extensions import db
    from models import Agency
    from services.gemini_letter import (
        build_fallback_complaint_letter,
        format_gemini_error,
        generate_complaint_letter,
    )

    agency = Agency.query.get(complaint.agency_id) if complaint.agency_id else None
    try:
        letter_text = generate_complaint_letter(complaint, complainant, agency)
        complaint.generated_letter = letter_text
        complaint.letter_generated = True
        db.session.commit()
        return True, None
    except Exception as exc:
        print(f'Gemini letter generation failed: {exc}')
        print(format_gemini_error(exc))
        complaint.generated_letter = build_fallback_complaint_letter(
            complaint,
            complainant,
            agency,
        )
        complaint.letter_generated = True
        db.session.commit()
        return True, 'fallback'


# ── Register ──
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form = _register_form_from_request()
        full_name = form.get('full_name', '').strip()
        email = form.get('email', '').strip()
        contact_number = form.get('contact_number', '').strip()
        barangay = form.get('barangay', '').strip()
        municipality = form.get('municipality', '').strip()
        password = form.get('password', '').strip()
        confirm_password = form.get('confirm_password', '').strip()

        # Validation checks
        if not all([full_name, email, contact_number, barangay, municipality, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return _render_register_form(form)

        if not contact_number.isdigit() or len(contact_number) != 11:
            flash('Contact number must contain numbers only and be exactly 11 digits.', 'danger')
            return _render_register_form(form)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return _render_register_form(form)

        password_error = _password_error(password)
        if password_error:
            flash(password_error, 'danger')
            return _render_register_form(form)

        # Check if email already exists
        existing_user = db.session.query(User).filter_by(email=email).first()
        if existing_user:
            flash('Email address is already registered.', 'danger')
            return _render_register_form(form)

        # Save to database (Assuming a helper method or direct instantiation)
        try:
            new_user = User(
                full_name=full_name,
                email=email,
                contact_number=contact_number,
                barangay=barangay,
                municipality=municipality
            )
            new_user.set_password(password) # Uses werkzeug security hashing
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('user.user_login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'danger')
            return _render_register_form(form)

    return _render_register_form()


@user_bp.route('/verify/<int:user_id>', methods=['GET', 'POST'])
def verify_account(user_id):
    from extensions import db
    from models import EmailVerification, User

    user = User.query.get_or_404(user_id)
    if user.status == 'active':
        flash('Your account is already verified. Please log in.', 'info')
        return redirect(url_for('user.user_login'))

    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        if not otp:
            flash('Please enter the OTP sent to your email.', 'danger')
            # compute remaining cooldown for template
            latest = EmailVerification.query.filter_by(user_id=user.id).order_by(EmailVerification.created_at.desc()).first()
            remaining = 0
            if latest:
                remaining = max(0, int((latest.created_at + timedelta(seconds=RESEND_COOLDOWN_SECONDS) - datetime.utcnow()).total_seconds()))
            return render_template('user/verify_account.html', user=user, resend_cooldown=remaining)

        verification = EmailVerification.query.filter_by(
            user_id=user.id,
            otp_code=otp,
            is_used=False,
        ).order_by(EmailVerification.created_at.desc()).first()

        if not verification or verification.expires_at < datetime.utcnow():
            flash('The OTP is invalid or has expired. Please request a new code.', 'danger')
            latest = EmailVerification.query.filter_by(user_id=user.id).order_by(EmailVerification.created_at.desc()).first()
            remaining = 0
            if latest:
                remaining = max(0, int((latest.created_at + timedelta(seconds=RESEND_COOLDOWN_SECONDS) - datetime.utcnow()).total_seconds()))
            return render_template('user/verify_account.html', user=user, resend_cooldown=remaining)

        verification.is_used = True
        user.status = 'active'
        db.session.commit()

        flash('Your account has been verified! Please log in.', 'success')
        return redirect(url_for('user.user_login'))

    latest = EmailVerification.query.filter_by(user_id=user.id).order_by(EmailVerification.created_at.desc()).first()
    remaining = 0
    if latest:
        remaining = max(0, int((latest.created_at + timedelta(seconds=RESEND_COOLDOWN_SECONDS) - datetime.utcnow()).total_seconds()))
    return render_template('user/verify_account.html', user=user, resend_cooldown=remaining)


@user_bp.route('/verify/<int:user_id>/resend', methods=['POST'])
def resend_verification_otp(user_id):
    from models import User

    user = User.query.get_or_404(user_id)
    if user.status == 'active':
        flash('Your account is already verified. Please log in.', 'info')
        return redirect(url_for('user.user_login'))
    from models import EmailVerification
    latest = EmailVerification.query.filter_by(user_id=user.id).order_by(EmailVerification.created_at.desc()).first()
    if latest:
        elapsed = (datetime.utcnow() - latest.created_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
            flash(f'Please wait {wait} seconds before requesting a new code.', 'warning')
            return redirect(url_for('user.verify_account', user_id=user.id))

    verification = _create_email_verification(user)
    sent = _send_account_verification_email(user, verification.otp_code)
    if sent:
        flash('A new OTP has been sent to your email address.', 'success')
    else:
        flash(
            'Unable to send a new OTP right now. Please try again later or contact support.',
            'warning',
        )
    return redirect(url_for('user.verify_account', user_id=user.id))


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

        if not user or not verify_password(user.password_hash, password):
            flash('Invalid credentials. Please try again.', 'danger')
            return render_template('user/login.html')

        if user.status == 'pending':
            flash(
                'Your account is not yet verified. Please check your email for the OTP ',
                'danger',
            )
            return render_template('user/login.html')

        if user.status == 'suspended':
            flash('Your account has been suspended. Please contact the administrator.', 'danger')
            return render_template('user/login.html')

        if user.status == 'deleted':
            flash('This account has been deleted.', 'danger')
            return render_template('user/login.html')

        logout_user()
        login_user(user)
        session.permanent = True
        return redirect(url_for('user.submit_complaint'))

    return render_template('user/login.html')


@user_bp.route('/profile')
@member_required
def profile():
    return render_template('user/profile.html')


@user_bp.route('/settings', methods=['GET', 'POST'])
@member_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'danger')
            elif not new_pw or len(new_pw) < 8:
                flash('New password must be at least 8 characters.', 'danger')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Password changed successfully.', 'success')

        elif action == 'update_notifications':
            current_user.email_notif = request.form.get('email_notif') == '1'
            current_user.inapp_notif = request.form.get('inapp_notif') == '1'
            db.session.commit()
            flash('Notification preferences updated.', 'success')

        elif action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            contact_number = request.form.get('contact_number', '').strip()
            barangay = request.form.get('barangay', '').strip()
            municipality = request.form.get('municipality', '').strip()
            if full_name:
                current_user.full_name = full_name
            if contact_number:
                current_user.contact_number = contact_number
            if barangay:
                current_user.barangay = barangay
            if municipality:
                current_user.municipality = municipality
            db.session.commit()
            flash('Profile updated successfully.', 'success')

        elif action == 'update_language':
            lang = request.form.get('default_lang', 'en-US')
            current_user.default_lang = lang
            db.session.commit()
            flash('Default language updated.', 'success')

        elif action == 'delete_account':
            confirm_pw = request.form.get('confirm_password', '')
            if not current_user.check_password(confirm_pw):
                flash('Password is incorrect. Account not deleted.', 'danger')
            else:
                current_user.status = 'deleted'
                db.session.commit()
                logout_user()
                flash('Your account has been deleted.', 'info')
                return redirect(url_for('user.user_login'))

        return redirect(url_for('user.settings'))

    return render_template('user/settings.html')


@user_bp.route('/logout')
@member_required
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
@member_required
def submit_complaint():
    if request.method == 'POST':
        # Safely pull form payload using request parameters
        selected_types = request.form.getlist('violation_type')
        custom_violation = request.form.get('custom_violation_type', '').strip()
        street_address = request.form.get('street_address', '').strip()
        barangay = request.form.get('barangay', '').strip()
        municipality = request.form.get('municipality', '').strip()
        date_incident = request.form.get('date_incident', '').strip()
        description = request.form.get('description', '').strip()
        photo = request.files.get('photo')

        # Build violation type string from checked boxes
        if not selected_types:
            flash('Please select at least one violation type.', 'danger')
            return _render_submit_form({})
        selected_types = [t for t in selected_types if t != 'Others']
        if 'Others' in request.form.getlist('violation_type'):
            if not custom_violation:
                flash('Please specify the violation type.', 'danger')
                return _render_submit_form({'violation_type': 'Others', 'custom_violation_type': custom_violation})
            selected_types.append(custom_violation)

        violation_type = ', '.join(selected_types)

        # Re-build structured dict payload to preserve field inputs during rendering fallbacks
        form = {
            'violation_type': violation_type,
            'custom_violation_type': custom_violation,
            'street_address': street_address,
            'barangay': barangay,
            'municipality': municipality,
            'date_incident': date_incident,
            'description': description
        }

        # Field validation requirements
        if not all([violation_type, street_address, barangay, municipality, date_incident, description]):
            flash('Please complete all mandatory form fields.', 'danger')
            return _render_submit_form(form)

        if len(description) < 20:
            flash(f'Description must be at least 20 characters (you entered {len(description)}).', 'danger')
            return _render_submit_form(form)

        # Date evaluation conversion check
        try:
            incident_date = date.fromisoformat(date_incident)
            if incident_date > date.today():
                flash('Date of incident cannot be a future date.', 'danger')
                return _render_submit_form(form)
        except ValueError:
            flash('Invalid date format processing.', 'danger')
            return _render_submit_form(form)

        # Photo processing routine block
        photo_path = None
        if photo and photo.filename != '':
            allowed_extensions = {'jpg', 'jpeg', 'png'}
            ext = photo.filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed_extensions:
                flash('Photo must be JPG or PNG only.', 'danger')
                return _render_submit_form(form)

            # Check file sizes via memory pointers
            photo.seek(0, 2)
            file_size = photo.tell()
            photo.seek(0)
            if file_size > 5 * 1024 * 1024:
                flash('Photo size must not exceed 5MB.', 'danger')
                return _render_submit_form(form)

            # Build standardized secure unique path string
            filename = secure_filename(photo.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            unique_name = f"{current_user.id}_{timestamp}_{filename}"

            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            photo_path = os.path.join(upload_folder, unique_name)
            photo.save(photo_path)

        # Automated sorting assignment
        agency_map = {
            'Illegal Dumping': 'DENR-EMB',
            'Air Pollution': 'DENR-EMB',
            'Water Pollution': 'DENR-EMB',
            'Toxic Waste': 'DENR-EMB',
            'Illegal Fishing': 'BFAR',
            'Marine Habitat Destruction': 'BFAR',
            'Poaching': 'BFAR',
            'Illegal Logging': 'DENR-FMB',
            'Unauthorized Timber Transport': 'DENR-FMB',
            'Kaingin': 'DENR-FMB',
            'Industrial Water Pollution': 'LLDA',
            'Illegal Reclamation': 'LLDA',
            'Others': 'DENR-EMB',
        }
        first_type = selected_types[0] if selected_types else 'Others'
        agency_name = agency_map.get(first_type, 'DENR-EMB')
        agency = Agency.query.filter_by(agency_name=agency_name).first()
        agency_id = agency.id if agency else None

        # Build DB instance record structure
        try:
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
        except Exception as e:
            db.session.rollback()
            flash('Database save failure encountered. Please check your data input.', 'danger')
            return _render_submit_form(form)

        # Automated document rendering dispatch call
        letter_ok, letter_error = _generate_letter_for_complaint(new_complaint, current_user)

        if letter_error == 'fallback':
            flash('Complaint submitted successfully. A formal letter was generated using the offline template.', 'info')
        elif letter_ok:
            flash('Complaint submitted successfully!', 'success')
        else:
            flash(f'Complaint saved. {letter_error}', 'warning')

        # Redirect user out to confirm success snapshot
        return redirect(url_for('user.complaint_submitted', complaint_id=new_complaint.id))

    # GET Request processing
    return _render_submit_form()


@user_bp.route('/submitted/<int:complaint_id>')
@member_required
def complaint_submitted(complaint_id):
    from models import Complaint

    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id:
        abort(403)
    return render_template('user/complaint_submitted.html', complaint=complaint)


def _letter_redirect(complaint_id, from_report=False):
    if from_report:
        return redirect(url_for('user.report_detail', complaint_id=complaint_id))
    return redirect(url_for('user.complaint_submitted', complaint_id=complaint_id))


@user_bp.route('/submitted/<int:complaint_id>/regenerate-letter', methods=['POST'])
@member_required
def regenerate_letter(complaint_id):
    from models import Complaint

    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id:
        abort(403)

    from_report = request.form.get('from') == 'report'

    if complaint.letter_generated and complaint.generated_letter:
        flash('Letter is already available for this complaint.', 'info')
        return _letter_redirect(complaint_id, from_report)

    letter_ok, letter_error = _generate_letter_for_complaint(complaint, current_user)
    if letter_ok:
        flash('Formal complaint letter generated successfully!', 'success')
    else:
        flash(letter_error, 'warning')

    return _letter_redirect(complaint_id, from_report)


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

        password_error = _password_error(password)
        if password_error:
            flash(password_error, 'danger')
            return render_template('user/reset_password.html', token=token)

        from models import User
        from extensions import db
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = hash_password(password)
            db.session.commit()
            flash('Password reset successfully! Please log in.', 'success')
            return redirect(url_for('user.user_login'))

    return render_template('user/reset_password.html', token=token)


def _complaint_photo_url(complaint):
    if not complaint.photo_path:
        return None
    path = complaint.photo_path.replace('\\', '/')
    if path.startswith('static/'):
        path = path[len('static/'):]
    return url_for('static', filename=path)


@user_bp.route('/my-reports')
@member_required
def my_reports():
    from models import Complaint

    status_filter = request.args.get('status', '').strip()
    violation_filter = request.args.get('violation_type', '').strip()
    search = request.args.get('q', '').strip()

    query = Complaint.query.filter_by(user_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if violation_filter:
        query = query.filter_by(violation_type=violation_filter)
    if search:
        normalized = search.upper().replace('#ING-', '').replace('ING-', '').strip()
        try:
            query = query.filter_by(id=int(normalized))
        except ValueError:
            query = query.filter(Complaint.id == -1)

    complaints = query.order_by(Complaint.created_at.desc()).all()
    all_statuses = ['Submitted', 'Under Review', 'Forwarded to Agency', 'Resolved']

    return render_template(
        'user/my_reports.html',
        complaints=complaints,
        status_filter=status_filter,
        violation_filter=violation_filter,
        search=search,
        all_statuses=all_statuses,
        violation_types=ALLOWED_VIOLATION_TYPES,
    )


@user_bp.route('/my-reports/<int:complaint_id>')
@member_required
def report_detail(complaint_id):
    from models import Complaint

    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id:
        abort(403)

    status_history = sorted(
        complaint.status_history,
        key=lambda entry: entry.updated_at,
        reverse=True,
    )
    photo_url = _complaint_photo_url(complaint)
    photo_filename = None
    if complaint.photo_path:
        photo_filename = complaint.photo_path.replace('\\', '/').rsplit('/', 1)[-1]

    return render_template(
        'user/report_detail.html',
        complaint=complaint,
        status_history=status_history,
        photo_url=photo_url,
        photo_filename=photo_filename,
    )


