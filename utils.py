import os
import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from werkzeug.security import check_password_hash, generate_password_hash


from flask import current_app
from itsdangerous import URLSafeTimedSerializer


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

        # start TLS if using common ports


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

        import traceback
        print('Email error:')
        traceback.print_exc()

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













import bcrypt

def hash_password(password):
    # This generates a secure, modern hash (usually scrypt by default in modern Flask)
    return generate_password_hash(password)

def verify_password(stored_hash, provided_password):
    if not stored_hash or not provided_password:
        return False
    # check_password_hash automatically detects if it's bcrypt, scrypt, or pbkdf2
    return check_password_hash(stored_hash, provided_password)


def is_bcrypt_hash(stored_hash: str) -> bool:
    """Return True if the stored hash uses bcrypt scheme."""
    if not stored_hash:
        return False
        
    # Standard bcrypt hashes always start with these prefixes
    valid_prefixes = ('$2a$', '$2b$', '$2y$')
    return stored_hash.startswith(valid_prefixes)


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

