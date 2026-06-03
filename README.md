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

Dependencies notes:
- This project uses `passlib[bcrypt]` for password hashing (bcrypt) and compatibility with legacy PBKDF2 hashes. Ensure you install dependencies with:

```powershell
pip install -r requirements.txt
```

The `utils.hash_password()` helper (in `utils.py`) is the recommended way to create password hashes for admin/manual account creation so they are compatible with the app's verification logic.
