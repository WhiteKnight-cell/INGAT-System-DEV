import os
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
def generate_complaint_letter(violation_type, description, barangay,
                               municipality, date_incident, complainant_name,
                               contact_number, agency_name):
    try:
        import google.generativeai as genai
        import os

        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Agency address mapping
        agency_addresses = {
            'DENR': 'Department of Environment and Natural Resources, Visayas Avenue, Diliman, Quezon City',
            'LLDA': 'Laguna Lake Development Authority, LLDA Complex, Laguna',
            'LGU': 'Local Government Unit Office, City Hall'
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
        1. Date (use {date_incident})
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