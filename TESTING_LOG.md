# TESTING_LOG (Integration Verification)

## Scope
- Sprint 8: System-Wide Integration Testing (User Story ING016)
- Backend modules: Flask routes, DB relationships, Gemini letter generation, email fallbacks, Google Maps privacy logic, exports (CSV/XLSX/PDF/DOCX where applicable)

## Environment
- App: Flask + Flask-Login + Flask-SQLAlchemy
- DB: SQLite (`ingat.db`)
- Test runner: `unittest`

---

## Test Suite
### Automated: `test_integration_sprint8.py`
Covers:
1. Flask routes / HTTP codes / protected-route redirects
2. Submitting a complaint creates `Complaint` rows and assigns an `Agency`
3. Gemini generation is mocked for success across all 5 violation types
4. Gemini API failure triggers fallback path (asserts redirect success; server-side fallback behavior)
5. Maps privacy audit (static HTML check that `showMap()` does not include `street_address`)
6. Export endpoints for PDF and DOCX compile and return correct mimetypes

---

## Execution Log
> Run command (from repo root):
- `venv\Scripts\python -m unittest -q test_integration_sprint8.py`

### Current status
- Pending execution in this session.

---

## Manual Frontend Checklists
### Voice input (from Sprint 8 / ING011)
- [ ] Open Submit Complaint page
- [ ] Click mic button
- [ ] Confirm label shows `Listening...`
- [ ] Confirm animated wave shows during recording
- [ ] Speak English; confirm transcript is appended to Description
- [ ] Click Re-record; confirm transcription clears and listening restarts
- [ ] Speak Filipino with language toggle set to **Filipino**; confirm transcript appears
- [ ] Stop Recording; confirm transcript is appended
- [ ] After transcript is appended, manually edit text in textarea; confirm no UI breaks

### Maps privacy (ING016 Task 4)
- [ ] Click “Show on Map”
- [ ] Confirm map query uses Barangay + Municipality only
- [ ] Confirm street address is not passed in the iframe src query string

---

## Expected Outcomes Summary
- All protected routes should redirect to correct login pages when unauthenticated
- Submitting a complaint should:
  - Create `Complaint`
  - Assign an `Agency` based on violation type mapping
- Gemini:
  - On API success (mocked): route should still complete and save complaint/letter
  - On API failure (mocked): route should complete and use offline fallback
- Maps privacy:
  - `showMap()` should not contain `street_address` in the URL logic
- Exports:
  - PDF export returns `application/pdf`
  - DOCX export returns DOCX mimetype

---

## Notes / Known Limitations
- SMTP/email verification fallback is not fully asserted with SMTP network calls; instead it is mocked/covered indirectly via letter generation flow.
- Gemini failure test asserts redirect behavior and that complaint submission path completes; deep assertion of fallback letter content can be added once status-history/email-trigger mechanism is confirmed in code.

