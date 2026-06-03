"""
Email diagnostics: loads .env, prints relevant vars, and attempts a test send to GMAIL_USER.
"""
import os

# try load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    p = os.path.join(os.getcwd(), '.env')
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line=line.strip()
                if not line or line.startswith('#'): continue
                if '=' in line:
                    k,v = line.split('=',1)
                    os.environ.setdefault(k.strip(), v.strip())

print('GMAIL_USER=', os.getenv('GMAIL_USER'))
print('GMAIL_APP_PASSWORD set=', bool(os.getenv('GMAIL_APP_PASSWORD')))
print('MAIL_SERVER=', os.getenv('MAIL_SERVER'))
print('MAIL_PORT=', os.getenv('MAIL_PORT'))
print('MAIL_DEBUG=', os.getenv('MAIL_DEBUG'))

# attempt a send
from utils import send_email
recipient = os.getenv('GMAIL_USER')
if recipient:
    print('Attempting test send to', recipient)
    ok = send_email(recipient, 'INGAT SMTP test', '<p>SMTP test</p>')
    print('send_email returned:', ok)
else:
    print('No recipient available; skipping send test')
