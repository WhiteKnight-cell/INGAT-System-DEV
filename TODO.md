# TODO.md — INGAT Sprint 5 (Admin)

## ING003B / ING003C (Admin Complaint Detail + Update Status)
- [x] Update `templates/admin/report_detail.html`:
  - [ ] Add AI letter download buttons (PDF/DOCX)
  - [ ] Add Google Maps iframe section (use municipality+barangay for URL; show street label above map without putting it into URL)
  - [ ] Add Update Status modal UI (dropdown + remarks + Save/Cancel)
- [ ] Update `routes/admin_routes.py`:
  - [ ] Add admin download routes for PDF/DOCX
  - [ ] Add POST route to update complaint status + remarks
  - [ ] Enforce one-direction status flow (Submitted → Under Review → Forwarded to Agency → Resolved)
  - [ ] Save `StatusHistory` entry with timestamp
  - [ ] Update `Complaint.status`
  - [ ] Send Gmail SMTP email notification to complainant after save

## ING002B (Admin Analytics Dashboard: Charts + Filters + Excel)
- [ ] Update `templates/admin/dashboard.html`:
  - [ ] Add Chart.js bar/line/pie charts
  - [ ] Add dashboard filter controls (violation type, status, barangay, date range)
  - [ ] Add Export to Excel (.xlsx) button
- [ ] Update `routes/admin_routes.py` (or add new route module):
  - [ ] Implement chart dataset generation with filters
  - [ ] Implement dashboard export-to-excel route using openpyxl

## Verification / Tests
- [ ] Manual test admin complaint detail:
  - [ ] Complaint info renders
  - [ ] AI letter preview renders
  - [ ] Google Maps shows barangay-level (municipality+barangay query)
  - [ ] PDF/DOCX downloads work
- [ ] Manual test update status:
  - [ ] Modal appears
  - [ ] Remarks required validation
  - [ ] One-direction flow validation
  - [ ] Status history saved and ordered correctly
  - [ ] Email notification sent
- [ ] Manual test dashboard:
  - [ ] Charts reflect database data
  - [ ] Filters update charts
  - [ ] Excel export downloads correct rows

