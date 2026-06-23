# --- Change the top of routes/admin_routes.py to look like this: ---
from flask import Blueprint, Response, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_user, logout_user, current_user
from datetime import datetime

# Local imports
from extensions import db
from models import AdminUser, Complaint, StatusHistory, Agency # <--- 💡 ADD 'Agency' HERE!
from utils import verify_password, send_email
from routes.auth import admin_required

# Blueprint definition
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

        # 1. Look for the admin
        admin = AdminUser.query.filter_by(email=email).first()
        
        print(f"DEBUG: Input Email: '{email}'")
        print(f"DEBUG: Admin found? {admin is not None}")
        
        if admin:
            # 2. Check the hash
            print(f"DEBUG: DB Hash: {admin.password_hash}")
            is_valid = verify_password(admin.password_hash, password)
            print(f"DEBUG: Password verification result: {is_valid}")
            
            if is_valid:
                login_user(admin)
                return redirect(url_for('admin.dashboard'))
        
        # If we reach here, it failed
        flash('Invalid credentials. Please try again.', 'danger')
        return render_template('admin/login.html')
        
    return render_template('admin/login.html')


# Import your model at the top if you haven't already
from models import Complaint
from sqlalchemy import func
from extensions import db

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # 1. Fetch the data for the table
    recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(10).all()
    
    # 2. Fetch ALL complaints to calculate counts accurately
    all_complaints = Complaint.query.all()
    
    # 3. Calculate the counts by checking the status strings
    total = len(all_complaints)
    pending = len([c for c in all_complaints if c.status in ['Submitted', 'Pending']])
    forwarded = len([c for c in all_complaints if c.status == 'Forwarded to Agency'])
    under_review = Complaint.query.filter_by(status='Under Review').count()
    resolved = len([c for c in all_complaints if c.status == 'Resolved'])
    
    return render_template('admin/dashboard.html', 
                           recent_complaints=recent_complaints,
                           total=total,
                           pending=pending,
                           under_review=under_review,
                           forwarded=forwarded,
                           resolved=resolved)



# ===== ING005 — Agency Management =====
@admin_bp.route('/agencies')
@admin_required
def manage_agencies():
    from models import Agency

    q = request.args.get('q', '').strip()

    query = Agency.query
    if q:
        # allow quick lookup by agency name or contact email
        query = query.filter(
            (Agency.agency_name.ilike(f'%{q}%')) | (Agency.contact_email.ilike(f'%{q}%'))
        )

    query = query.order_by(Agency.created_at.desc())
    agencies = query.all()

    return render_template(
        'admin/manage_agencies.html',
        agencies=agencies,
        q=q,
    )


@admin_bp.route('/agencies/add', methods=['GET', 'POST'])
@admin_required
def agency_add():
    from extensions import db
    from models import Agency

    all_violation_types = VIOLATION_TYPES

    if request.method == 'POST':
        agency_name = request.form.get('agency_name', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        status = request.form.get('status', 'active').strip()
        violation_types_multi = request.form.getlist('violation_types')

        if not agency_name:
            flash('Agency name is required.', 'danger')
            return render_template(
                'admin/agency_form.html',
                mode_title='Add Agency',
                form_action=url_for('admin.agency_add'),
                agency={},
                all_violation_types=all_violation_types,
                selected_violation_types=violation_types_multi,
            )

        if status not in {'active', 'inactive'}:
            flash('Invalid status.', 'danger')
            return redirect(url_for('admin.agency_add'))

        if not contact_email:
            flash('Contact email is required.', 'danger')
            return redirect(url_for('admin.agency_add'))

        if not contact_number.isdigit() or len(contact_number) != 11:
            flash('Contact number must be exactly 11 digits.', 'danger')
            return render_template(
                'admin/agency_form.html',
                mode_title='Add Agency',
                form_action=url_for('admin.agency_add'),
                agency={},
                all_violation_types=all_violation_types,
                selected_violation_types=violation_types_multi,
            )

        # store as comma-separated string
        violation_types_multi = violation_types_multi or []
        invalid = [v for v in violation_types_multi if v not in all_violation_types]
        if invalid:
            flash('Invalid violation types selected.', 'danger')
            return redirect(url_for('admin.agency_add'))

        violation_types_csv = ','.join(violation_types_multi)
        if not violation_types_csv:
            flash('Please select at least one violation type.', 'danger')
            return redirect(url_for('admin.agency_add'))

        agency = Agency(
            agency_name=agency_name,
            contact_email=contact_email,
            contact_number=contact_number,
            violation_types=violation_types_csv,
            status=status,
        )
        db.session.add(agency)
        db.session.commit()

        flash('Agency added successfully.', 'success')
        return redirect(url_for('admin.manage_agencies'))

    return render_template(
        'admin/agency_form.html',
        mode_title='Add Agency',
        form_action=url_for('admin.agency_add'),
        agency={},
        all_violation_types=all_violation_types,
        selected_violation_types=[],
    )


@admin_bp.route('/agencies/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def agency_edit(id: int):
    from extensions import db
    from models import Agency

    agency = Agency.query.get_or_404(id)
    all_violation_types = VIOLATION_TYPES

    selected_violation_types = []
    if agency.violation_types:
        selected_violation_types = [v.strip() for v in agency.violation_types.split(',') if v.strip()]

    if request.method == 'POST':
        agency_name = request.form.get('agency_name', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        status = request.form.get('status', 'active').strip()
        violation_types_multi = request.form.getlist('violation_types')

        if not agency_name:
            flash('Agency name is required.', 'danger')
            return redirect(url_for('admin.agency_edit', id=id))

        if status not in {'active', 'inactive'}:
            flash('Invalid status.', 'danger')
            return redirect(url_for('admin.agency_edit', id=id))

        if not contact_email:
            flash('Contact email is required.', 'danger')
            return redirect(url_for('admin.agency_edit', id=id))

        if not contact_number.isdigit() or len(contact_number) != 11:
            flash('Contact number must be exactly 11 digits.', 'danger')
            return redirect(url_for('admin.agency_edit', id=id))

        violation_types_multi = violation_types_multi or []
        invalid = [v for v in violation_types_multi if v not in all_violation_types]
        if invalid:
            flash('Invalid violation types selected.', 'danger')
            return redirect(url_for('admin.agency_edit', id=id))

        violation_types_csv = ','.join(violation_types_multi)
        if not violation_types_csv:
            flash('Please select at least one violation type.', 'danger')
            return redirect(url_for('admin.agency_edit', id=id))

        agency.agency_name = agency_name
        agency.contact_email = contact_email
        agency.contact_number = contact_number
        agency.violation_types = violation_types_csv
        agency.status = status

        db.session.commit()
        flash('Agency updated successfully.', 'success')
        return redirect(url_for('admin.manage_agencies'))

    return render_template(
        'admin/agency_form.html',
        mode_title='Edit Agency',
        form_action=url_for('admin.agency_edit', id=id),
        agency=agency,
        all_violation_types=all_violation_types,
        selected_violation_types=selected_violation_types,
    )




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

@admin_bp.route('/agencies/delete/<int:agency_id>', methods=['POST'])
@admin_required
def delete_agency(agency_id):
    agency = Agency.query.get_or_404(agency_id)
    
    try:
        linked_complaints = Complaint.query.filter_by(agency_id=agency.id).all()
        for complaint in linked_complaints:
            complaint.agency_id = None 
            
        db.session.delete(agency)
        db.session.commit()
        flash(f'Agency "{agency.agency_name}" was successfully deleted.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while trying to delete this agency.', 'danger')
        
    return redirect(url_for('admin.manage_agencies'))

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


@admin_bp.route('/analytics')
@admin_required
def analytics_report():
    # Basic page render (extend later with real aggregation + Chart.js data endpoints)
    from models import Complaint
    from sqlalchemy import func

    # Populate optional dropdowns
    violation_types = sorted({c.violation_type for c in Complaint.query.all()})
    barangays = sorted({c.barangay for c in Complaint.query.all() if c.barangay})

    # Status breakdown (simple counts)
    status_counts = (
        db.session.query(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )

    total = sum(count for _, count in status_counts) or 1
    # Map to required statuses order
    status_map = {s: c for s, c in status_counts}
    status_order = ['Submitted', 'Under Review', 'Forwarded to Agency', 'Resolved']
    status_rows = [
        {
            'status': s,
            'count': status_map.get(s, 0),
            'percent': int(round((status_map.get(s, 0) / total) * 100)),
        }
        for s in status_order
    ]

    return render_template(
        'admin/analytics_reports.html',
        status_rows=status_rows,
        status_order=status_order,
        violation_types=violation_types,
        barangays=barangays,
        violation_type=request.args.get('violation_type', ''),
        barangay_filter=request.args.get('barangay', ''),
        date_from=request.args.get('date_from', ''),
        date_to=request.args.get('date_to', ''),
    )


@admin_bp.route('/reports/<int:complaint_id>')
@admin_required
def report_detail(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Fetch all active agencies from your Agency database table
    agencies = Agency.query.filter_by(status='active').all()
    
    return render_template('admin/report_detail.html', 
                           complaint=complaint, 
                           agencies=agencies) # Pass the list here



@admin_bp.route('/users')
@admin_required
def manage_users():
    """ING006 — manage registered users (search, filter, suspend/reactivate, export)."""
    from models import User, Complaint
    from extensions import db
    from sqlalchemy import func

    q = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip()

    # Base query
    query = User.query

    if q:
        like = f'%{q}%'
        query = query.filter(or_(User.full_name.ilike(like), User.email.ilike(like)))

    if status_filter:
        query = query.filter(User.status == status_filter)

    # For "Total Reports": compute via Complaint aggregation
    # We'll fetch users first then compute totals via grouped complaint query for efficiency.
    users = query.order_by(User.created_at.desc()).all()

    user_ids = [u.id for u in users]
    totals_by_user = {}
    if user_ids:
        totals = (
            db.session.query(Complaint.user_id, func.count(Complaint.id))
            .filter(Complaint.user_id.in_(user_ids))
            .group_by(Complaint.user_id)
            .all()
        )
        totals_by_user = {uid: total for uid, total in totals}

    # Attach total_reports to each user object for template convenience
    for u in users:
        u.total_reports = totals_by_user.get(u.id, 0)

    statuses = ['active', 'suspended']

    return render_template(
        'admin/manage_users.html',
        users=users,
        search=q,
        status_filter=status_filter,
        statuses=statuses,
    )


@admin_bp.route('/users/suspend/<int:user_id>', methods=['POST'])
@admin_required
def suspend_user(user_id: int):
    from models import User
    from extensions import db

    user = User.query.get_or_404(user_id)
    user.status = 'suspended'
    db.session.commit()
    flash('User suspended successfully.', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/reactivate/<int:user_id>', methods=['POST'])
@admin_required
def reactivate_user(user_id: int):
    from models import User
    from extensions import db

    user = User.query.get_or_404(user_id)
    user.status = 'active'
    db.session.commit()
    flash('User reactivated successfully.', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/export')
@admin_required
def export_users_csv():
    """Export users for ING006."""
    import csv
    import io
    from models import User, Complaint
    from extensions import db
    from sqlalchemy import func

    q = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip()

    query = User.query
    if q:
        like = f'%{q}%'
        query = query.filter(or_(User.full_name.ilike(like), User.email.ilike(like)))

    if status_filter:
        query = query.filter(User.status == status_filter)

    users = query.order_by(User.created_at.desc()).all()
    user_ids = [u.id for u in users]

    totals_by_user = {}
    if user_ids:
        totals = (
            db.session.query(Complaint.user_id, func.count(Complaint.id))
            .filter(Complaint.user_id.in_(user_ids))
            .group_by(Complaint.user_id)
            .all()
        )
        totals_by_user = {uid: total for uid, total in totals}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Date Registered', 'Total Reports', 'Status'])

    for u in users:
        writer.writerow([
            u.id,
            u.full_name,
            u.email,
            u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else '',
            totals_by_user.get(u.id, 0),
            u.status,
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=ingat_users.csv'},
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

    from extensions import db


    from models import Complaint
    from services.letter_export import build_letter_pdf

    complaint = Complaint.query.get_or_404(complaint_id)

    if not (complaint.letter_generated and complaint.generated_letter):
        flash('No generated letter is available for this complaint.', 'warning')

    if not complaint.generated_letter:
        flash('No generated letter available for this complaint.', 'warning')

        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    pdf_buffer = build_letter_pdf(complaint.generated_letter, complaint.id)
    filename = f'INGAT_Complaint_{complaint.id:04d}.pdf'

    # return BytesIO buffer

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

    if not (complaint.letter_generated and complaint.generated_letter):
        flash('No generated letter is available for this complaint.', 'warning')

    if not complaint.generated_letter:
        flash('No generated letter available for this complaint.', 'warning')

        return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    docx_buffer = build_letter_docx(complaint.generated_letter, complaint.id)
    filename = f'INGAT_Complaint_{complaint.id:04d}.docx'

    ##return __import__('flask').send_file

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
    complaint = Complaint.query.get_or_404(complaint_id)
    new_status = request.form.get('new_status', '').strip()
    remarks = request.form.get('remarks', '').strip()
    
    # READ THE SELECTED AGENCY ID FROM STEP 2
    agency_id = request.form.get('agency_id')
    
    # ... keep your existing validations here ...

    try:
        sh = StatusHistory(
            complaint_id=complaint.id,
            previous_status=complaint.status,
            new_status=new_status,
            remarks=remarks,
            updated_by=current_user.id,
            updated_at=datetime.utcnow()
        )
        
        # LINK THE AGENCY TO THE COMPLAINT IF PROVIDED
        if agency_id:
            complaint.agency_id = int(agency_id)
            
        complaint.status = new_status
        db.session.add(sh)
        db.session.commit()
        flash('Status updated successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating.', 'danger')

    return redirect(url_for('admin.report_detail', complaint_id=complaint_id))

    # 4. Email Notification
    try:
        complainant = complaint.complainant
        if complainant and complainant.email:
            subject = f'INGAT — Complaint Status Updated: #{complaint.id}'
            body = f"<p>Hello {complainant.full_name}, your complaint status is now <strong>{new_status}</strong>.</p>"
            send_email(complainant.email, subject, body)
    except Exception as e:
        print(f'Email notification failed: {e}')

    flash('Status updated successfully.', 'success')
    return redirect(url_for('admin.report_detail', complaint_id=complaint_id))




@admin_bp.route('/logout')
@admin_required
def logout():
    logout_user()
    return redirect(url_for('admin.admin_login'))

