import secrets
from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contact_number = db.Column(db.String(11), nullable=False)
    barangay = db.Column(db.String(100), nullable=False)
    municipality = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(20), default='active')
    email_notif = db.Column(db.Boolean, default=True)
    inapp_notif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    complaints = db.relationship('Complaint', backref='complainant', lazy=True)
    email_verifications = db.relationship('EmailVerification', backref='user', lazy=True)

    # 🛠️ Fixed Password Utilities to integrate with your registration backend route
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ⚠️ Note: If your LoginManager user_loader expects an integer string, use "return str(self.id)".
    def get_id(self):
        return f'user-{self.id}'


class EmailVerification(db.Model):
    __tablename__ = 'email_verifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    otp_code = db.Column(db.String(10), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdminUser(db.Model, UserMixin):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email_notif = db.Column(db.Boolean, default=True)
    inapp_notif = db.Column(db.Boolean, default=True)
    session_token = db.Column(db.String(64), default=lambda: secrets.token_hex(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🛠️ Added security hashing helpers to Admin users too
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f'admin-{self.id}'


class AdminLog(db.Model):
    __tablename__ = 'admin_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('AdminUser', backref='logs', lazy=True)


class Agency(db.Model):
    __tablename__ = 'agencies'
    
    id = db.Column(db.Integer, primary_key=True)
    agency_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(11), nullable=False)
    violation_types = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    complaints = db.relationship('Complaint', backref='agency', lazy=True)


class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=True)
    violation_type = db.Column(db.String(100), nullable=False)
    street_address = db.Column(db.String(255), nullable=False)
    barangay = db.Column(db.String(100), nullable=False)
    municipality = db.Column(db.String(100), nullable=False)
    date_incident = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo_path = db.Column(db.String(255), nullable=True)
    generated_letter = db.Column(db.Text, nullable=True)
    letter_generated = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='Submitted')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    status_history = db.relationship('StatusHistory', backref='complaint', lazy=True)


class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    previous_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)