# INGAT-System-DEV

INGAT offers a user-friendly web platform that allows Filipino community members to report environmental violations in simple language. It aims to assist Filipino residents, barangay officials, and student advocates who want to address these issues but may lack the knowledge or resources to file formal complaints.

## Run locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:5000/ | Redirects to member login |
| http://127.0.0.1:5000/user/register | Community member registration |
| http://127.0.0.1:5000/user/login | Community member login |
| http://127.0.0.1:5000/user/submit | Submit complaint (login required) |
| http://127.0.0.1:5000/admin/login | Admin login |

Create the first admin account (one time):

```bash
python -c "from app import app; from extensions import db; from models import AdminUser; from utils import hash_password; app.app_context().push(); db.session.add(AdminUser(email='admin@ingat.com', password_hash=hash_password('Admin@1234'))); db.session.commit(); print('Admin created')"
```

Default agencies (DENR, LLDA, LGU) are seeded automatically on first run.

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey) for AI complaint letters (Sprint 3).

Password hashing and dependencies:
- This project uses `passlib`'s CryptContext with `pbkdf2_sha256` as the primary hashing scheme in development to avoid platform-specific bcrypt backend issues.
- The application supports verification of legacy Werkzeug `scrypt` / `pbkdf2:sha256` hashes and will re-hash them to the current scheme on first successful login (rehash-on-login). The centralized helpers in `utils.py` (`hash_password`, `verify_password`, `is_bcrypt_hash`) manage hashing and verification.
- If you prefer `bcrypt` in production, install `bcrypt` and `passlib[bcrypt]`, ensure the target environment has a compatible `bcrypt` backend, and be aware of bcrypt's 72-byte input limitation.

Environment variables (copy `.env.example` -> `.env`):
- `GMAIL_USER` — SMTP account email used to send verification/reset emails.
- `GMAIL_APP_PASSWORD` — app password or SMTP password for `GMAIL_USER`.
- `MAIL_DEBUG` — set to `1` to enable SMTP debug output during testing.
- `SECRET_KEY` — Flask secret key used for session and token signing.

Install dependencies and run:

```powershell
pip install -r requirements.txt
```

Use the `utils.hash_password()` helper when creating admin or manual accounts so stored hashes are compatible with the application's verification logic.
