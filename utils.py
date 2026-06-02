import os
import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def send_email(to_email, subject, body):
    try:
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

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f'Email error: {e}')
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
