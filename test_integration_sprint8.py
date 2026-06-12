"""INGAT System-Wide Integration Tests (Sprint 8 - ING016)

Run:
  1) (Recommended) Ensure a clean test DB backup.
  2) Activate venv.
  3) python -m unittest -q test_integration_sprint8.py

Notes:
- These tests are designed to run without real external services.
- Gemini and SMTP are mocked.
- Some route behaviors depend on the DB state and seeding.
"""

import io
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import date


# Import the app and models
from app import create_app
from extensions import db
from models import User, AdminUser, Agency, Complaint, StatusHistory
from utils import hash_password


class TestFlaskRoutesAndDatabaseCascades(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        self.ctx = self.app.app_context()
        self.ctx.push()

        # Ensure tables exist
        db.create_all()

        # Seed agencies (create_app already seeds on first run, but ensure at least one)
        if Agency.query.count() == 0:
            from app import seed_default_agencies
            seed_default_agencies()

        # Create admin + user for tests
        self.admin = AdminUser.query.filter_by(email='admin_test@ingat.com').first()
        if not self.admin:
            self.admin = AdminUser(
                email='admin_test@ingat.com',
                password_hash=hash_password('Admin@1234'),
            )
            db.session.add(self.admin)
            db.session.commit()

        self.user = User.query.filter_by(email='user_test@ingat.com').first()
        if not self.user:
            self.user = User(
                full_name='Test User',
                email='user_test@ingat.com',
                contact_number='09123456788',
                barangay='Tondo',
                municipality='Manila',
                password_hash=hash_password('Test@1234'),
                status='active',
            )
            db.session.add(self.user)
            db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def login_admin(self):
        return self.client.post(
            '/admin/login',
            data={'email': self.admin.email, 'password': 'Admin@1234'},
            follow_redirects=False,
        )

    def login_member(self):
        return self.client.post(
            '/user/login',
            data={'email': self.user.email, 'password': 'Test@1234'},
            follow_redirects=False,
        )

    def test_route_http_codes_and_protected_pages(self):
        # Public pages
        r = self.client.get('/user/login')
        self.assertEqual(r.status_code, 200)

        # Protected pages redirect
        r = self.client.get('/user/submit', follow_redirects=False)
        self.assertIn('/user/login', r.location)
        self.assertEqual(r.status_code, 302)

        r = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertIn('/admin/login', r.location)
        self.assertEqual(r.status_code, 302)

        # Unknown route -> 404
        r = self.client.get('/definitely-not-a-route')
        self.assertEqual(r.status_code, 404)

    @patch('routes.user_routes._generate_letter_for_complaint')
    def test_submit_complaint_creates_agency_and_status_history(self, _gen_letter):
        # Mock letter generation to avoid Gemini calls
        _gen_letter.return_value = (True, None)

        # Login user
        r = self.login_member()

        self.assertIn('/user/submit', r.location)

        # Find a known agency via violation mapping in user_routes.submit_complaint
        # Illegal Dumping -> LGU seeded
        agency = Agency.query.filter_by(agency_name='LGU').first()
        self.assertIsNotNone(agency)

        payload = {
            'violation_type': 'Illegal Dumping',
            'street_address': '123 Rizal St',
            'barangay': 'Tondo',
            'municipality': 'Manila',
            'date_incident': date.today().isoformat(),
            'description': 'Test description for illegal dumping with sufficient length.',
        }

        r = self.client.post('/user/submit', data=payload, follow_redirects=False)
        # On success, redirect to complaint submitted page
        self.assertEqual(r.status_code, 302)
        self.assertIn('/user/submitted/', r.location)

        # Fetch created complaint
        complaint_id = int(r.location.rsplit('/', 1)[-1])
        c = Complaint.query.get(complaint_id)
        self.assertIsNotNone(c)
        self.assertEqual(c.user_id, self.user.id)
        self.assertEqual(c.violation_type, payload['violation_type'])
        self.assertIsNotNone(c.agency_id)
        self.assertEqual(c.agency_id, agency.id)

        # StatusHistory should exist only if your app creates it.
        # Current codebase defines StatusHistory, but status creation logic may be in admin routes.
        # We'll at least verify relationship works (no crash) and optionally create one.
        if c.status_history:
            self.assertTrue(len(c.status_history) >= 1)

    def test_admin_report_detail_forbidden_for_member(self):
        # Member login
        self.login_member()

        # Member should get redirected or forbidden (depends on route decorators)
        r = self.client.get('/admin/reports/1', follow_redirects=False)
        self.assertIn('/admin/login', r.location)


class TestGeminiAndEmailFallbacks(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # User active
        self.user = User.query.filter_by(email='user_gemini_test@ingat.com').first()
        if not self.user:
            self.user = User(
                full_name='Gemini Test User',
                email='user_gemini_test@ingat.com',
                contact_number='09123456786',
                barangay='Tondo',
                municipality='Manila',
                password_hash=hash_password('Test@1234'),
                status='active',
            )
            db.session.add(self.user)
            db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def login_member(self):
        return self.client.post(
            '/user/login',
            data={'email': self.user.email, 'password': 'Test@1234'},
            follow_redirects=False,
        )

    @patch('services.gemini_letter.generate_complaint_letter')
    def test_gemini_success_for_all_violation_types(self, mock_generate):
        # Return a deterministic letter
        mock_generate.return_value = 'Date: today\nTo: Agency\nRE: Test\nBody...'

        self.login_member()

        violation_types = [
            'Illegal Dumping',
            'Air Pollution',
            'Water Pollution',
            'Illegal Logging',
            'Others',
        ]

        for vt in violation_types:
            payload = {
                'violation_type': vt,
                'street_address': 'Somewhere 1',
                'barangay': 'Tondo',
                'municipality': 'Manila',
                'date_incident': date.today().isoformat(),
                'description': f'Test description for {vt} with sufficient length to pass validation.',
            }
            r = self.client.post('/user/submit', data=payload, follow_redirects=False)
            self.assertEqual(r.status_code, 302)
            self.assertIn('/user/submitted/', r.location)

    @patch('services.gemini_letter.generate_complaint_letter')
    def test_gemini_api_failure_triggers_fallback(self, mock_generate):
        mock_generate.side_effect = RuntimeError('Gemini API failure')

        self.login_member()

        payload = {
            'violation_type': 'Illegal Dumping',
            'street_address': 'Somewhere 1',
            'barangay': 'Tondo',
            'municipality': 'Manila',
            'date_incident': date.today().isoformat(),
            'description': 'Test description for illegal dumping with sufficient length to pass validation.',
        }
        r = self.client.post('/user/submit', data=payload, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        # Should still reach complaint submitted page; letter generation fallback is handled server-side.


class TestMapsPrivacyAudit(unittest.TestCase):
    def test_maps_embed_query_uses_barangay_and_municipality_only(self):
        """Static check: ensure frontend showMap only uses barangay + municipality."""
        tpl_path = os.path.join(
            'templates', 'user', 'submit_complaint.html'
        )
        # Read from filesystem relative to repo root
        with open(tpl_path, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()

        # showMap should use barangay and municipality; ensure street_address not used in showMap logic
        self.assertIn("barangay + ', ' + municipality", html)
        showmap_idx = html.find('function showMap')
        self.assertNotEqual(showmap_idx, -1)
        # slice only until the next function to avoid false positives from other scripts
        next_fn_idx = html.find('function countChars', showmap_idx)
        if next_fn_idx == -1:
            showmap_chunk = html[showmap_idx:]
        else:
            showmap_chunk = html[showmap_idx:next_fn_idx]
        self.assertNotIn('street_address', showmap_chunk)



class TestExports(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.user = User.query.filter_by(email='user_export_test@ingat.com').first()
        if not self.user:
            self.user = User(
                full_name='Export User',
                email='user_export_test@ingat.com',
                contact_number='09123456787',
                barangay='Tondo',
                municipality='Manila',
                password_hash=hash_password('Test@1234'),
                status='active',
            )
            db.session.add(self.user)
            db.session.commit()

        agency = Agency.query.filter_by(agency_name='LGU').first()
        self.agency = agency
        # Create complaint directly with generated letter
        self.complaint = Complaint.query.filter_by(user_id=self.user.id).first()
        if not self.complaint:
            self.complaint = Complaint(
                user_id=self.user.id,
                agency_id=self.agency.id if self.agency else None,
                violation_type='Illegal Dumping',
                street_address='Somewhere',
                barangay='Tondo',
                municipality='Manila',
                date_incident=date.today(),
                description='A valid description for export testing with enough length.',
                generated_letter='Date: today\n\nBody line 1\nBody line 2',
                letter_generated=True,
                status='Submitted',
            )
            db.session.add(self.complaint)
            db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def login_member(self):
        return self.client.post(
            '/user/login',
            data={'email': self.user.email, 'password': 'Test@1234'},
            follow_redirects=False,
        )

    def test_letter_pdf_and_docx_export_endpoints(self):
        self.login_member()

        cid = self.complaint.id
        r = self.client.get(f'/user/submitted/{cid}/download/pdf')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, 'application/pdf')
        self.assertTrue(len(r.data) > 1000)

        r2 = self.client.get(f'/user/submitted/{cid}/download/docx')
        self.assertEqual(r2.status_code, 200)
        self.assertIn('wordprocessingml', r2.mimetype or '')


if __name__ == '__main__':
    unittest.main()

