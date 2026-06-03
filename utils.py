import os
import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from passlib.context import CryptContext

from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def send_email(to_email, subject, body):
    try:
        # allow overriding SMTP settings via env
        mail_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        mail_port = int(os.getenv('MAIL_PORT', '587'))
        mail_debug = os.getenv('MAIL_DEBUG', '0') == '1'

        gmail_user = os.getenv('GMAIL_USER')
        gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        if not gmail_user or not gmail_password:
            print('Email skipped: GMAIL_USER or GMAIL_APP_PASSWORD not set in .env')
            return False

        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(mail_server, mail_port, timeout=20)
        if mail_debug:
            server.set_debuglevel(1)
        # start TLS if using common ports
        try:
            server.starttls()
        except Exception:
            pass
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        import traceback
        print('Email error:')
        traceback.print_exc()
        return False


def generate_reset_token(email):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset')


def verify_reset_token(token, expiration=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return s.loads(token, salt='password-reset', max_age=expiration)
    except Exception:
        return None


def generate_otp_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(to_email, full_name, otp_code):
    subject = 'INGAT — Verify Your Account'
    body = f"""
    <h3>Hi {full_name},</h3>
    <p>Thank you for registering with INGAT.</p>
    <p>Your verification code is:</p>
    <p style='font-size: 24px; font-weight: 700; letter-spacing: 0.2em;'>{otp_code}</p>
    <p>This code will expire in 15 minutes.</p>
    <p>If you did not create an account, please ignore this email.</p>
    """
    return send_email(to_email, subject, body)


# Use passlib CryptContext to support bcrypt and fallback verification of pbkdf2_sha256.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "scrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt via passlib CryptContext."""
    return pwd_context.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    """Verify a plaintext password against stored hash, supporting multiple schemes."""
    if not stored_hash:
        return False
    try:
        scheme = pwd_context.identify(stored_hash)
        if scheme is not None:
            return pwd_context.verify(password, stored_hash)
    except Exception:
        pass

    # Fallback: try Werkzeug's check_password_hash for legacy werkzeug hashes (scrypt, pbkdf2:sha256, etc.)
    try:
        return check_password_hash(stored_hash, password)
    except Exception:
        return False


def is_bcrypt_hash(stored_hash: str) -> bool:
    """Return True if the stored hash uses bcrypt scheme according to passlib."""
    if not stored_hash:
        return False
    try:
        scheme = pwd_context.identify(stored_hash)
        return scheme in ('bcrypt', 'bcrypt_sha256')
    except Exception:
        return False
