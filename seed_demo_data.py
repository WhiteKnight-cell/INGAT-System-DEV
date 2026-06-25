"""seed_demo_data.py — Live panel demo database seeding (Sprint 8 / ING017)

Usage:
  1) Activate venv
  2) Ensure ingat.db exists (run app once or run this script)
  3) python seed_demo_data.py

What it does:
- Seeds demo users (multiple citizen accounts)
- Seeds demo complaints across diverse violation types
- Links complaints to seeded Agencies (DENR/LLDA/LGU)
- Creates StatusHistory transitions per complaint to populate admin timeline

Safety:
- This script will NOT delete existing data.
- It uses deterministic emails; running multiple times is idempotent.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta

from app import create_app
from extensions import db
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash


DEMO_ADMIN_EMAIL = "[EMAIL_ADDRESS]"

DEMO_USERS = [
    {
        "full_name": "Citizen One",
        "email": "citizen1@test.local",
        "contact_number": "09120000001",
        "barangay": "Tondo",
        "municipality": "Manila",
        "password": "Test@1234",
        "status": "active",
    },
    {
        "full_name": "Barangay Captain",
        "email": "captain1@test.local",
        "contact_number": "09120000002",
        "barangay": "Diliman",
        "municipality": "Quezon City",
        "password": "Test@1234",
        "status": "active",
    },
    {
        "full_name": "Citizen Two (Negative Test)",
        "email": "citizen2@test.local",
        "contact_number": "09120000003",
        "barangay": "Sampaloc",
        "municipality": "Manila",
        "password": "Test@1234",
        "status": "active",
    },
]


DEMO_AGENCY_EMAILS = {
    "DENR": "denr@gov.ph",
    "LLDA": "llda@gov.ph",
    "LGU": "lgu@gov.ph",
}


DEMO_COMPLAINTS = [
    {
        "user_email": "citizen1@test.local",
        "violation_type": "Illegal Dumping",
        "street_address": "Blk 12, Example St",
        "barangay": "Tondo",
        "municipality": "Manila",
        "days_ago": 12,
        "description": "We observed repeated dumping near the barangay area. Please investigate and address the issue.",
    },
    {
        "user_email": "captain1@test.local",
        "violation_type": "Air Pollution",
        "street_address": "Along River Road",
        "barangay": "Diliman",
        "municipality": "Quezon City",
        "days_ago": 9,
        "description": "There is frequent smoke and odor from an unknown source. It affects nearby residents daily.",
    },
    {
        "user_email": "citizen1@test.local",
        "violation_type": "Water Pollution",
        "street_address": "Near drainage canal",
        "barangay": "Sampaloc",
        "municipality": "Manila",
        "days_ago": 6,
        "description": "Water in the canal looks discolored and smells strongly. Residents are concerned about pollution.",
    },
    {
        "user_email": "captain1@test.local",
        "violation_type": "Illegal Logging",
        "street_address": "Forest edge",
        "barangay": "Diliman",
        "municipality": "Quezon City",
        "days_ago": 4,
        "description": "We noticed signs of illegal tree cutting in the area. Please inspect and take action if needed.",
    },
    {
        "user_email": "citizen2@test.local",
        "violation_type": "Others",
        "street_address": "Market back area",
        "barangay": "Sampaloc",
        "municipality": "Manila",
        "days_ago": 2,
        "description": "Other environmental concern: persistent improper disposal and unmanaged waste accumulation in the vicinity.",
    },
]


def upsert_admin():
    from models import AdminUser

    admin = AdminUser.query.filter_by(email=DEMO_ADMIN_EMAIL).first()
    if admin:
        return admin

    admin = AdminUser(email=DEMO_ADMIN_EMAIL, password_hash = hash_password("Admin@1234"))
    db.session.add(admin)
    db.session.commit()
    print("Seeded admin:", admin.email)
    return admin


def upsert_users():
    from models import User

    seeded = []
    for u in DEMO_USERS:
        existing = User.query.filter_by(email=u["email"]).first()
        if existing:
            seeded.append(existing)
            continue

        user = User(
            full_name=u["full_name"],
            email=u["email"],
            contact_number=u["contact_number"],
            barangay=u["barangay"],
            municipality=u["municipality"],
            password_hash = hash_password(u["password"]),
            status=u["status"],
            email_notif=True,
            created_at=datetime.utcnow(),
        )
        db.session.add(user)
        seeded.append(user)

    db.session.commit()
    print(f"Seeded users: {len(seeded)}")
    return seeded


def ensure_agencies():
    from models import Agency

    # Create/Update using default names if missing
    for agency_name, email in DEMO_AGENCY_EMAILS.items():
        agency = Agency.query.filter_by(agency_name=agency_name).first()
        if agency:
            continue

        agency = Agency(
            agency_name=agency_name,
            contact_email=email,
            contact_number="09170000000",
            violation_types="",
            status="active",
            created_at=datetime.utcnow(),
        )
        db.session.add(agency)

    db.session.commit()
    return Agency.query.all()


def agency_for_violation(violation_type: str):
    # Mirror the routing logic in routes/user_routes.py
    if violation_type == "Illegal Dumping":
        return "LGU"
    if violation_type == "Air Pollution":
        return "DENR"
    if violation_type == "Water Pollution":
        return "LLDA"
    if violation_type == "Illegal Logging":
        return "DENR"
    if violation_type == "Others":
        return "LGU"
    return "LGU"


def seed_complaints_and_history(admin):
    from models import User, Complaint, StatusHistory
    for c in DEMO_COMPLAINTS:
    # Query the user using the email field inside the current complaint item
        user = db.session.execute(
        db.select(User).filter_by(email=c['user_email'])
    ).scalar_one_or_none()
    # Idempotent key = (user_email, violation_type, days_ago)
    # (Simple and stable for demo)
    seeded = 0


    # easier without meta-types

    from models import User

    for c in DEMO_COMPLAINTS:
        user = User.query.filter_by(email=c["user_email"]).first()
        if not user:
            continue

        # Find existing complaint by matching key fields
        existing = Complaint.query.filter_by(
            user_id=user.id,
            violation_type=c["violation_type"],
            barangay=c["barangay"],
            municipality=c["municipality"],
            street_address=c["street_address"],
        ).order_by(Complaint.created_at.desc()).first()

        if existing:
            continue

        agency_name = agency_for_violation(c["violation_type"])
        from models import Agency

        agency = Agency.query.filter_by(agency_name=agency_name).first()

        created_date = date.today() - timedelta(days=c["days_ago"])

        complaint = Complaint(
            user_id=user.id,
            agency_id=agency.id if agency else None,
            violation_type=c["violation_type"],
            street_address=c["street_address"],
            barangay=c["barangay"],
            municipality=c["municipality"],
            date_incident=created_date,
            description=c["description"],
            photo_path=None,
            generated_letter=(
                f"Date: {date.today().strftime('%B %d, %Y')}\n\n"
                f"(Demo) Formal letter for {c['violation_type']} in {c['barangay']}.\n"
                f"Complainant: {user.full_name}"
            ),
            letter_generated=True,
            status="Submitted",
            created_at=datetime.utcnow() - timedelta(days=c["days_ago"]),
        )
        db.session.add(complaint)
        db.session.flush()  # get complaint.id

        # Populate status history timeline
        timeline = [
            (None, "Submitted", "Complaint submitted via INGAT."),
            ("Submitted", "Under Review", "Initial verification and review."),
            ("Under Review", "Forwarded to Agency", "Routed to the appropriate agency."),
            ("Forwarded to Agency", "Resolved", "Marked as resolved after action."),
        ]

        now = datetime.utcnow() - timedelta(days=c["days_ago"])
        for idx, (prev, new, remarks) in enumerate(timeline):
            sh = StatusHistory(
                complaint_id=complaint.id,
                previous_status=prev,
                new_status=new,
                remarks=remarks,
                updated_by=admin.id,
                updated_at=now + timedelta(minutes=idx * 10),
            )
            db.session.add(sh)

        complaint.status = "Resolved"
        db.session.add(complaint)

        db.session.commit()
        seeded += 1

    print(f"Seeded complaints: {seeded}")


def main():
    app = create_app()

    with app.app_context():
        from models import StatusHistory  # noqa: F401

        ensure_agencies()
        admin = upsert_admin()
        upsert_users()
        seed_complaints_and_history(admin)

        print("Demo data seeding completed.")


if __name__ == "__main__":
    main()

