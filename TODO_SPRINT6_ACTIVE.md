# TODO_SPRINT6_ACTIVE

## ING005 — Agency Management
- [x] Existing implementation present (`/admin/agencies`, add/edit, templates)
- [ ] Verify validation rules: backend email format + multi-select at least one + contact 11 digits
- [ ] Add/update integration tests in `test_smoke.py` for add/edit + validation

## ING006 — Manage Users
- [ ] Add routes in `routes/admin_routes.py`: `/admin/users`, suspend, reactivate, export
- [ ] Create `templates/admin/manage_users.html`
- [ ] Update `templates/admin/dashboard.html` sidebar link for Manage Users
- [ ] Update/extend integration tests in `test_smoke.py`

## ING014 — Email Notifications
- [x] Refactor admin status update to send email only when `complainant.email_notif` is True

- [ ] Email content: Complaint ID, Updated Status, Admin Remarks, and link to `/user/my-reports`
- [ ] Ensure email errors do not rollback status update; log error
- [ ] Add/extend integration tests in `test_smoke.py` (mock SMTP)

