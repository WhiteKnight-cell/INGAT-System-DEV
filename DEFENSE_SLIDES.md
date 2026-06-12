# DEFENSE_SLIDES.md — Capstone Defense Outline (Sprint 8)

## Slide 1 — Title
- INGAT: Community Environmental Complaint System
- Sprint 8: UAT and Final Evaluation

---

## Slide 2 — The Problem
- Many community members want to report environmental violations but lack:
  - knowledge to prepare formal documents
  - confidence to file complaints correctly
  - access to structured guidance
- Admins need consistent, searchable complaint records.

---

## Slide 3 — The Solution
- INGAT provides:
  - simple complaint submission form
  - automatic routing to the correct agency
  - formal letter generation (Gemini-backed, with offline fallback)
  - status tracking and admin reporting

---

## Slide 4 — Key Features (User)
- Account creation with email verification
- Complaint submission with validation
- Voice input to help users describe incidents faster
- Complaint status tracking
- Letter preview + downloads (PDF/DOCX)

---

## Slide 5 — Key Features (Admin)
- Manage complaints through filters and sorting
- Report detail view with status history timeline
- CSV exports for analytics/reporting workflows

---

## Slide 6 — Tech Stack
- Backend: Flask, Flask-Login, Flask-SQLAlchemy
- DB: SQLite
- Gemini Letter Generation: `services/gemini_letter.py`
- Offline Fallback: `build_fallback_complaint_letter()`
- Exports:
  - PDF: `services/letter_export.py`
  - DOCX: `services/letter_export.py`
- Frontend templates: Jinja2

---

## Slide 7 — Architecture Overview
- Blueprint-based routes:
  - `/user/*`
  - `/admin/*`
- Models:
  - User, AdminUser, Agency, Complaint, StatusHistory
- Services layer for AI + exports

---

## Slide 8 — Privacy & Ethical Considerations
- **Maps privacy**:
  - embed query uses Barangay + Municipality only
  - avoids embedding street-level address at the map layer
- **Speech accessibility**:
  - supports English/Filipino voice input toggle
  - transcript still editable before submission
- **Security**:
  - authentication gates for protected routes
  - 403 permissions for cross-user complaint access

---

## Slide 9 — Live Demo Plan (Minute-by-Minute)
1. (0–2 min) Login as Citizen, submit a complaint.
2. (2–4 min) Use voice input to populate description.
3. (4–6 min) Show map (barangay/municipality only) and submit.
4. (6–7 min) Preview generated letter.
5. (7–8 min) Download PDF and DOCX.
6. (8–10 min) Switch to Admin login.
7. (10–12 min) Filter reports, open detail, update status.
8. (12–13 min) Export CSV.
9. (13–14 min) Brief ethical/privacy statement during transitions.

---

## Slide 10 — Evaluation Results (Sprint 8)
- UAT outcome: **READY FOR PANEL DEMO**
- Backend integration tests: **7/7 pass**
- Gemini fallback verified in failure scenario
- Privacy audit verified on Maps embed logic

---

## Slide 11 — Closing
- Recap value to communities and administrators
- Future improvements:
  - richer analytics exports
  - more granular map privacy
  - extended notification workflows

