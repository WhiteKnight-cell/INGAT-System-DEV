import os
import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from itsdangerous import URLSafeTimedSerializer
from passlib.context import CryptContext
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash


def send_email(to_email, subject, body):
    """Send an HTML email via SMTP.

    Expects these environment variables in .env:
    - GMAIL_USER
    - GMAIL_APP_PASSWORD
    Optional:
    - MAIL_SERVER (default smtp.gmail.com)
    - MAIL_PORT (default 587)
    - MAIL_DEBUG (set to 1 to enable SMTP debug output)

    Returns True on success, False otherwise.
    """
    try:
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

        # start TLS if supported
        try:
            server.starttls()
        except Exception:
            pass

        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print('Email error:')
        print(e)
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
# Note: passlib will choose the scheme in the hash based on the stored value.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "scrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using the current passlib CryptContext."""
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

    # Fallback for legacy Werkzeug hashes
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


# Backwards-compatible legacy name (some older code may import it)
generate_password = generate_password_hash


def generate_complaint_letter(
    violation_type,
    description,
    barangay,
    municipality,
    date_incident,
    complainant_name,
    contact_number,
    agency_name,
):
    """Legacy helper kept for compatibility. Prefer services/gemini_letter.py."""
    try:
        import google.generativeai as genai

        api_key = os.getenv('GEMINI_API_KEY', '').strip()
        if not api_key or api_key == 'your_gemini_api_key_here':
            raise ValueError('GEMINI_API_KEY is not configured in .env')

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        agency_addresses = {
            'DENR': 'Department of Environment and Natural Resources, Visayas Avenue, Diliman, Quezon City',
            'LLDA': 'Laguna Lake Development Authority, LLDA Complex, Laguna',
            'LGU': 'Local Government Unit Office, City Hall',
        }
        agency_address = agency_addresses.get(agency_name, 'Concerned Government Agency')

        prompt = f"""
        Write a formal complaint letter in English with the following details:

        - Complainant Name: {complainant_name}
        - Contact Number: {contact_number}
        - Violation Type: {violation_type}
        - Location: Barangay {barangay}, {municipality}
        - Date of Incident: {date_incident}
        - Description: {description}
        - Addressed To: {agency_name} ({agency_address})

        Format the letter professionally with:
        1. Date (use {date_incident} as reference; letter date may be today).
        2. Recipient agency name and address
        3. Subject line
        4. Formal salutation
        5. Body paragraphs explaining the violation
        6. Request for action
        7. Closing with complainant name and contact number

        Keep it formal, concise, and professional.
        Do not include any placeholders or brackets.
        Write the complete letter only — no explanations before or after.
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return None

