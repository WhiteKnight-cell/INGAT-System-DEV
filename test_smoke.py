"""Quick smoke tests for merged admin + user app. Run: python test_smoke.py"""
import re
import uuid

from app import app
from extensions import db
from models import AdminUser, Agency, Complaint, User
from utils import hash_password
from werkzeug.security import generate_password_hash


def run_tests():
    client = app.test_client()
    passed = 0
    failed = 0

    def ok(name):
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    def fail(name, detail=""):
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))

    print("\n=== INGAT smoke tests ===\n")

    # Public pages load
    for path, name in [
        ("/", "Home redirect"),
        ("/user/login", "User login page"),
        ("/user/register", "User register page"),
        ("/admin/login", "Admin login page"),
    ]:
        r = client.get(path, follow_redirects=False)
        if path == "/":
            if r.status_code in (302, 308):
                ok(name)
            else:
                fail(name, f"status {r.status_code}")
        elif r.status_code == 200 and b"INGAT" in r.data:
            ok(name)
        else:
            fail(name, f"status {r.status_code}")

    # Protected routes redirect when not logged in
    r = client.get("/user/submit")
    if r.status_code == 302 and "/user/login" in (r.location or ""):
        ok("Submit complaint requires login")
    else:
        fail("Submit complaint requires login", r.location)

    r = client.get("/user/my-reports")
    if r.status_code == 302 and "/user/login" in (r.location or ""):
        ok("My reports requires login")
    else:
        fail("My reports requires login", r.location)

    r = client.get("/admin/dashboard")
    if r.status_code == 302 and "/admin/login" in (r.location or ""):
        ok("Admin dashboard requires login")
    else:
        fail("Admin dashboard requires login", r.location)

    r = client.get("/admin/reports")
    if r.status_code == 302 and "/admin/login" in (r.location or ""):
        ok("Manage reports requires admin login")
    else:
        fail("Manage reports requires admin login", r.location)

    with app.app_context():
        agencies = Agency.query.count()
        if agencies >= 3:
            ok(f"Agencies seeded ({agencies})")
        else:
            fail("Agencies seeded", str(agencies))

        admin = AdminUser.query.filter_by(email="admin@ingat.com").first()
        if not admin:
            admin = AdminUser(
                email="admin@ingat.com",
                password_hash=hash_password("Admin@1234"),

                password_hash=generate_password_hash("Admin@1234"),
            )
            db.session.add(admin)
            db.session.commit()
            ok("Admin account created for test")
        else:
            ok("Admin account exists")

        test_email = f"smoke_{uuid.uuid4().hex[:8]}@test.local"
        test_user = User.query.filter_by(email=test_email).first()
        if not test_user:
            test_user = User(
                full_name="Smoke Test User",
                email=test_email,
                contact_number="09123456789",
                barangay="Tondo",
                municipality="Manila",
                password_hash=hash_password("Test@1234"),
                password_hash=generate_password_hash("Test@1234"),
            )
            db.session.add(test_user)
            db.session.commit()

    # Admin login
    r = client.post(
        "/admin/login",
        data={"email": "admin@ingat.com", "password": "Admin@1234"},
        follow_redirects=False,
    )
    if r.status_code == 302 and "/admin/dashboard" in (r.location or ""):
        ok("Admin login")
    else:
        fail("Admin login", f"status {r.status_code} loc {r.location}")

    r = client.get("/admin/dashboard")
    if r.status_code == 200 and b"Complaint Dashboard" in r.data:
        ok("Admin dashboard loads")
    else:
        fail("Admin dashboard loads", f"status {r.status_code}")

    r = client.get("/user/submit")
    if r.status_code == 302 and "/admin/dashboard" in (r.location or ""):
        ok("Admin blocked from member submit page")
    else:
        fail("Admin blocked from member submit", r.location)

    client.get("/admin/logout", follow_redirects=True)

    # Member login
    r = client.post(
        "/user/login",
        data={"email": test_email, "password": "Test@1234"},
        follow_redirects=False,
    )
    if r.status_code == 302 and "/user/submit" in (r.location or ""):
        ok("Member login")
    else:
        fail("Member login", f"status {r.status_code} loc {r.location}")

    r = client.get("/user/submit")
    if r.status_code == 200 and b"Submit" in r.data:
        ok("Submit complaint form loads")
    else:
        fail("Submit complaint form loads", f"status {r.status_code}")

    r = client.get("/admin/dashboard")
    if r.status_code == 302 and "/admin/login" in (r.location or ""):
        ok("Member blocked from admin dashboard")
    else:
        fail("Member blocked from admin dashboard", r.location)

    # Submit complaint
    r = client.post(
        "/user/submit",
        data={
            "violation_type": "Illegal Dumping",
            "street_address": "123 Test St",
            "barangay": "Tondo",
            "municipality": "Manila",
            "date_incident": "2026-05-01",
            "description": "Smoke test illegal dumping near river bank area.",
        },
        follow_redirects=False,
    )
    if r.status_code == 302 and "/user/submitted/" in (r.location or ""):
        ok("Complaint submitted")
        m = re.search(r"/user/submitted/(\d+)", r.location or "")
        cid = int(m.group(1)) if m else None
    else:
        fail("Complaint submitted", f"status {r.status_code} loc {r.location}")
        cid = None

    if cid:
        with app.app_context():
            c = Complaint.query.get(cid)
            if c and c.violation_type == "Illegal Dumping" and c.agency_id:
                agency = Agency.query.get(c.agency_id)
                if agency and agency.agency_name == "LGU":
                    ok("Auto-routed to LGU for Illegal Dumping")
                else:
                    fail("Auto-routing", agency.agency_name if agency else "no agency")
            else:
                fail("Complaint saved", str(c))

        r = client.get(f"/user/submitted/{cid}")
        if r.status_code == 200 and b"#ING-" in r.data:
            ok("Complaint success page")
        else:
            fail("Complaint success page", f"status {r.status_code}")

        r = client.get(f"/user/submitted/{cid}")
        if b"Try Generate Letter Again" in r.data or b"Preview Generated Letter" in r.data:
            ok("Complaint page shows letter preview or retry")
        else:
            fail("Complaint page letter UI", "missing preview/retry controls")

        r = client.post(f"/user/submitted/{cid}/regenerate-letter", follow_redirects=False)
        if r.status_code == 302 and f"/user/submitted/{cid}" in (r.location or ""):
            ok("Regenerate letter route")
        else:
            fail("Regenerate letter route", f"status {r.status_code} loc {r.location}")


        with app.app_context():
            c = Complaint.query.get(cid)
            if c:
                c.generated_letter = (
                    'Date: May 1, 2026\n\n'
                    'To: DENR\n\n'
                    'RE: Test Violation\n\n'
                    'This is a sample formal complaint letter for export testing.\n\n'
                    'Respectfully yours,\nSmoke Test User'
                )
                c.letter_generated = True
                db.session.commit()

        r = client.get(f"/user/submitted/{cid}/download/pdf")
        if r.status_code == 200 and r.mimetype == 'application/pdf':
            ok("Download letter PDF")
        else:
            fail("Download letter PDF", f"status {r.status_code}")

        r = client.get(f"/user/submitted/{cid}/download/docx")
        if r.status_code == 200 and 'wordprocessingml' in (r.mimetype or ''):
            ok("Download letter DOCX")
        else:
            fail("Download letter DOCX", f"status {r.status_code} type {r.mimetype}")

        r = client.get("/user/my-reports")
        if r.status_code == 200 and b"My Reports" in r.data and b"ING-" in r.data:
            ok("My reports list shows complaint")
        else:
            fail("My reports list", f"status {r.status_code}")

        r = client.get(f"/user/my-reports?q=ING-{cid:04d}")
        if r.status_code == 200 and f"ING-{cid:04d}".encode() in r.data:
            ok("My reports complaint ID search")
        else:
            fail("My reports complaint ID search", f"status {r.status_code}")

        r = client.get("/user/my-reports?violation_type=Illegal+Dumping&status=Submitted")
        if r.status_code == 200 and b"Illegal Dumping" in r.data:
            ok("My reports filters")
        else:
            fail("My reports filters", f"status {r.status_code}")

        r = client.get(f"/user/my-reports/{cid}")
        if r.status_code == 200 and b"Illegal Dumping" in r.data and b"AI-Generated Letter" in r.data:
            ok("Report detail page loads")
        else:
            fail("Report detail page", f"status {r.status_code}")

        r = client.get("/user/my-reports?status=Resolved")
        if r.status_code == 200 and (
            b"No reports found" in r.data or b"No complaints match" in r.data
        ):
            ok("My reports status filter")
        else:
            fail("My reports status filter", f"status {r.status_code}")

        other_email = f"other_{uuid.uuid4().hex[:8]}@test.local"

        with app.app_context():
            other_user = User(
                full_name="Other User",
                email=other_email,
                contact_number="09111111111",
                barangay="Quiapo",
                municipality="Manila",
                password_hash=hash_password("Test@1234"),
            )
            db.session.add(other_user)
            db.session.commit()

        client.get("/user/logout", follow_redirects=True)
        client.post(
            "/user/login",
            data={"email": other_email, "password": "Test@1234"},
            follow_redirects=True,
        )
        r = client.get(f"/user/my-reports/{cid}")
        if r.status_code == 403:
            ok("Report detail forbidden for other user")
        else:
            fail("Report detail forbidden for other user", f"status {r.status_code}")

        client.get("/user/logout", follow_redirects=True)
        client.post(
            "/admin/login",
            data={"email": "admin@ingat.com", "password": "Admin@1234"},
            follow_redirects=False,
        )

        r = client.get("/admin/reports")
        if r.status_code == 200 and b"Manage Reports" in r.data and b"ING-" in r.data:
            ok("Admin manage reports list")
        else:
            fail("Admin manage reports list", f"status {r.status_code}")

        r = client.get(f"/admin/reports?q=Smoke+Test+User&violation_type=Illegal+Dumping&sort=status")
        if r.status_code == 200 and b"Smoke Test User" in r.data:
            ok("Admin manage reports search and filters")
        else:
            fail("Admin manage reports search and filters", f"status {r.status_code}")

        r = client.get(f"/admin/reports/{cid}")
        if r.status_code == 200 and b"Complaint Information" in r.data:
            ok("Admin report detail")
        else:
            fail("Admin report detail", f"status {r.status_code}")

        r = client.get("/admin/reports/export")
        if r.status_code == 200 and "text/csv" in (r.mimetype or ""):
            ok("Admin reports CSV export")
        else:
            fail("Admin reports CSV export", f"status {r.status_code} type {r.mimetype}")


    print(f"\n=== Results: {passed} passed, {failed} failed ===\n")
    return failed == 0


if __name__ == "__main__":
    import sys

    sys.exit(0 if run_tests() else 1)
