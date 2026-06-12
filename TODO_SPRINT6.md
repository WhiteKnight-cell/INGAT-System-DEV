# TODO_SPRINT6.md — Sprint 6 (Admin first)

## ING005 — Agency Management (Admin)
- [ ] Create `templates/admin/manage_agencies.html`
- [ ] Create `templates/admin/agency_form.html`
- [ ] Add routes in `routes/admin_routes.py`:
  - [ ] GET `/admin/agencies`
  - [ ] GET, POST `/admin/agencies/add`
  - [ ] GET, POST `/admin/agencies/edit/<int:id>`
- [ ] Server-side validation (flash messages)
- [ ] Multi-select violation types UI + store as comma-separated string
- [ ] Status badge + Active/Inactive toggle
- [ ] Integration tests for adding and editing agencies

## ING006 — Manage Users (Admin)
- [ ] Create `templates/admin/manage_users.html`
- [ ] Add routes in `routes/admin_routes.py`:
  - [ ] GET `/admin/users`
  - [ ] POST `/admin/users/suspend/<int:id>`
  - [ ] POST `/admin/users/reactivate/<int:id>`
  - [ ] GET `/admin/users/export`
- [ ] Search + status filtering + report counts
- [ ] Update auth so suspended users cannot log in (user-side already done)
- [ ] Integration tests for suspend/reactivate/login block/CSV export/filtering/search

## ING014 — Email Notifications (Admin integration)
- [ ] Create `utils/email_service.py` with `send_notification(...)`
- [ ] Add notification template usage
- [ ] Refactor admin status update route to call notification service
- [ ] Send email only when `user.email_notif == True`
- [ ] Ensure email failures do NOT rollback status update
- [ ] Integration tests mocking SMTP

