from flask import Blueprint, Response, render_template, redirect, url_for, flash, request
from utils import verify_password
from flask_login import login_user, logout_user
import csv
import io
from sqlalchemy import or_

from routes.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

VIOLATION_TYPES = [
    'Illegal Dumping',
    'Air Pollution',
    'Water Pollution',
    'Illegal Logging',
    'Others',
]

STATUS_OPTIONS = ['Submitted', 'Under Review', 'Forwarded to Agency', 'Resolved']


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

        if not admin or not verify_password(admin.password_hash, password):
            flash('Invalid credentials. Please try again.', 'danger')
            return render_template('admin/login.html')

        login_user(admin)
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/login.html')


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')


def _filtered_complaints_query():
    from models import Complaint, User

    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    violation_filter = request.args.get('violation_type', '').strip()
    sort = request.args.get('sort', 'newest').strip()

    query = Complaint.query.join(User, Complaint.user_id == User.id)
    if search:
        search_like = f'%{search}%'
        normalized = search.upper().replace('#ING-', '').replace('ING-', '').strip()
        search_filters = [
            User.full_name.ilike(search_like),
            Complaint.barangay.ilike(search_like),
            Complaint.municipality.ilike(search_like),
        ]
        if normalized.isdigit():
            search_filters.append(Complaint.id == int(normalized))
        query = query.filter(or_(*search_filters))
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    if violation_filter:
        query = query.filter(Complaint.violation_type == violation_filter)

    if sort == 'oldest':
        query = query.order_by(Complaint.created_at.asc())
    elif sort == 'status':
        query = query.order_by(Complaint.status.asc(), Complaint.created_at.desc())
    else:
        query = query.order_by(Complaint.created_at.desc())

    return query


@admin_bp.route('/reports')
@admin_required
def manage_reports():
    page = request.args.get('page', 1, type=int)
    paginated = _filtered_complaints_query().paginate(page=page, per_page=10, error_out=False)
    return render_template(
        'admin/manage_reports.html',
        complaints=paginated.items,
        search=request.args.get('q', '').strip(),
        status_filter=request.args.get('status', '').strip(),
        violation_filter=request.args.get('violation_type', '').strip(),
        sort=request.args.get('sort', 'newest').strip(),
        statuses=STATUS_OPTIONS,
        violation_types=VIOLATION_TYPES,
        pagination=paginated,
    )


@admin_bp.route('/reports/export')
@admin_required
def export_reports_csv():
    complaints = _filtered_complaints_query().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Complaint ID',
        'Complainant',
        'Violation Type',
        'Barangay',
        'Municipality',
        'Date Submitted',
        'Status',
    ])
    for complaint in complaints:
        writer.writerow([
            f'ING-{complaint.id:04d}',
            complaint.complainant.full_name,
            complaint.violation_type,
            complaint.barangay,
            complaint.municipality,
            complaint.created_at.strftime('%Y-%m-%d %H:%M'),
            complaint.status,
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=ingat_reports.csv'},
    )


@admin_bp.route('/reports/<int:complaint_id>')
@admin_required
def report_detail(complaint_id):
    from models import Complaint

    complaint = Complaint.query.get_or_404(complaint_id)
    status_history = sorted(
        complaint.status_history,
        key=lambda entry: entry.updated_at,
        reverse=True,
    )
    return render_template(
        'admin/report_detail.html',
        complaint=complaint,
        status_history=status_history,
        status_options=STATUS_OPTIONS,
    )



def _can_transition(prev_status: str, new_status: str) -> bool:
    flow = {
        'Submitted': 'Under Review',
        'Under Review': 'Forwarded to Agency',
        'Forwarded to Agency': 'Resolved',
        'Resolved': None,
    }
    return flow.get(prev_status) == new_status


@admin_bp.route('/reports/<int:complaint_id>/download/pdf')
@admin_required
def download_letter_pdf(complaint_id):
    from models import Complaint
    from services.letter_export import build_letter_pdf

    complaint = Complaint.query.get_or_404(complaint_id)
    if not complaint.generated_letter:
        flash('No generated letter available for this complaint.', 'warning')
        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    pdf_buffer = build_letter_pdf(complaint.generated_letter, complaint.id)
    filename = f'INGAT_Complaint_{complaint.id:04d}.pdf'

    # send_file is imported indirectly in some setups; import locally for safety
    from flask import send_file

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@admin_bp.route('/reports/<int:complaint_id>/download/docx')
@admin_required
def download_letter_docx(complaint_id):
    from models import Complaint
    from services.letter_export import build_letter_docx

    complaint = Complaint.query.get_or_404(complaint_id)
    if not complaint.generated_letter:
        flash('No generated letter available for this complaint.', 'warning')
        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    docx_buffer = build_letter_docx(complaint.generated_letter, complaint.id)
    filename = f'INGAT_Complaint_{complaint.id:04d}.docx'

    from flask import send_file

    return send_file(
        docx_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=filename,
    )


@admin_bp.route('/reports/<int:complaint_id>/update-status', methods=['POST'])
@admin_required
def update_status(complaint_id):
    from models import Complaint, StatusHistory, AdminUser
    from extensions import db
    from flask import current_app
    from utils import send_email

    complaint = Complaint.query.get_or_404(complaint_id)

    new_status = request.form.get('new_status', '').strip()
    remarks = request.form.get('remarks', '').strip()

    if new_status not in STATUS_OPTIONS:
        flash('Invalid status selected.', 'danger')
        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    if not remarks:
        flash('Remarks are required.', 'danger')
        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    prev_status = complaint.status
    if prev_status == new_status:
        flash('Status is already set to the selected value.', 'info')
        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    if not _can_transition(prev_status, new_status):
        flash('Invalid status transition. Please follow the one-direction flow.', 'danger')
        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    # Save status history
    sh = StatusHistory(
        complaint_id=complaint.id,
        previous_status=prev_status,
        new_status=new_status,
        remarks=remarks,
        updated_by=current_user.id if isinstance(current_user, AdminUser) else None,
    )
    db.session.add(sh)

    # Update complaint status
    complaint.status = new_status
    db.session.commit()

    # Email complainant notification (if email exists)
    try:
        complainant = complaint.complainant
        if complainant and complainant.email:
            subject = 'INGAT — Complaint Status Updated'
            body = f"""
            <h3>INGAT — Status Update</h3>
            <p>Hello {complainant.full_name},</p>
            <p>Your complaint <strong>#ING-{complaint.id:04d}</strong> status has been updated to:</p>
            <p style='font-size:18px;font-weight:700'>{new_status}</p>
            <p><strong>Remarks:</strong></p>
            <p style='white-space:pre-wrap'>{remarks}</p>
            <p>Thank you.</p>
            """
            send_email(complainant.email, subject, body)
    except Exception:
        # Don’t break status update if email fails
        pass

    flash('Status updated successfully.', 'success')
    return redirect(url_for('admin.report_detail', complaint_id=complaint_id))


@admin_bp.route('/logout')
@admin_required
def logout():
    logout_user()
    return redirect(url_for('admin.admin_login'))

