# TODO_SPRINT7_ACTIVE

## ING007A — Analytics & Reports Dashboard
- [x] Implement `/admin/analytics` route (filters + dataset aggregation)

- [ ] Create `templates/admin/analytics_dashboard.html` (filters + charts + status table)
- [ ] Add Chart.js charts (Top 5 violation types, Top 5 barangays, Monthly volume)
- [ ] Validate status summary table logic (Pending/Under Review/In Progress/Resolved/Rejected)
- [ ] Add integration tests for filters + chart dataset counts + status table

## ING007B — Export Analytics Reports
- [ ] Implement `/admin/analytics/export/xlsx` route using openpyxl
- [ ] Implement `/admin/analytics/export/pdf` route using fpdf2
- [ ] Ensure exports reflect current filters
- [ ] Add integration tests for export routes (xlsx + pdf) and filter consistency

## ING015 — User Profile & Notification Settings
- [ ] Implement user profile routes in `routes/user_routes.py` (GET + POST profile; password change; notifications)
- [ ] Create `templates/user/profile.html`
- [ ] Add input validation + security checks (member auth, verify current password, email read-only)
- [ ] Add integration tests for profile update, password change validation, notification toggles

## Final
- [ ] Run full test suite (`python test_smoke.py` and analytics/profile tests)
- [ ] Produce final verification checklist vs acceptance criteria

