# UAT_LOG.md — Sprint 8 (ING017) | UAT and Final Evaluation Deliverables

## Version / Scope
- **Version**: v1.0
- **Scope**: End-to-end UAT for Sprint 8 flows (Auth, Complaint submission, Voice input, Maps privacy behavior, Gemini letter generation fallback, Admin status handling, Exports, Analytics/export utilities).

## Assumptions / Test Setup
- Application runs locally using `python app.py`.
- `.env` is configured for email if needed (SMTP may be intentionally disabled for fallback scenarios).
- Gemini API key may be set; UAT includes both **Gemini success** and **Gemini failure** scenarios.

## Test Users (5 distinct roles)
1. **Citizen (Community Member)**: `citizen1@test.local`
2. **Barangay Captain (Citizen role but with reviewer mindset)**: `captain1@test.local`
3. **Agency Reviewer (Admin role)**: `reviewer1@test.local`
4. **Super Admin (Admin role)**: `admin@ingat.com`
5. **Negative Test User (for permissions)**: `citizen2@test.local`

> Note: If you only have one Admin account in the DB, log in as that account for Admin/Reviewer steps.

---

## UAT Sessions & Feedback Log

### Session 1 — Citizen: Registration → Verify OTP → Login → Submit Complaint (Maps + Voice)
**User**: Citizen (`citizen1@test.local`)

**Preconditions**
- User exists in DB as `status=pending`.
- OTP email delivery may be simulated or inspected in logs.

**Steps**
1. Visit `/user/register`.
2. Register with valid fields and strong password.
3. Go to verification page `/user/verify/<id>` and enter OTP.
4. Login via `/user/login`.
5. Navigate to `/user/submit`.
6. Use **voice input** to fill description; verify language toggle.
7. Enter Barangay + Municipality and click **Show on Map**.
8. Submit complaint across multiple violation types.

**Expected Results / Pass Criteria**
- ✅ Registration succeeds; status becomes `active` after OTP.
- ✅ Voice input appends transcript to description field.
- ✅ Maps embed logic uses **Barangay + Municipality** only (no street-level address is passed to the embed query logic).
- ✅ Complaint submission redirects to `/user/submitted/<complaint_id>`.

**Actual Feedback**
- Voice input: transcript appended correctly; toggling English/Filipino updated recognition language.
- Maps: embed query constructed with Barangay + Municipality.
- Complaint submission: letter preview UI displayed.

**Verdict**: **PASS**

---

### Session 2 — Citizen: Gemini Letter Generation Success
**User**: Citizen (`citizen1@test.local`)

**Steps**
1. Submit a complaint.
2. Click **Generate Letter** (or wait for auto-generated letter, depending on UI).
3. Verify letter preview.

**Expected Results / Pass Criteria**
- ✅ Gemini request returns a non-empty letter.
- ✅ Letter is stored in DB fields `generated_letter` and `letter_generated=True`.

**Actual Feedback**
- Letter appears in preview and exports function.

**Verdict**: **PASS**

---

### Session 3 — Citizen: Gemini Failure → Offline Fallback Letter
**User**: Citizen (`captain1@test.local`)

**Steps**
1. Set Gemini API key to an invalid value OR temporarily block external Gemini calls.
2. Submit a complaint.
3. Verify that fallback letter is generated automatically.

**Expected Results / Pass Criteria**
- ✅ Route does not crash.
- ✅ UI indicates fallback or successfully generated letter.
- ✅ Export (PDF/DOCX) works with fallback text.

**Actual Feedback**
- Gemini failure logged; fallback letter used successfully.

**Verdict**: **PASS**

---

### Session 4 — Negative Permission Check: Other user cannot view complaint detail
**User**: Negative Test User (`citizen2@test.local`)

**Steps**
1. Submit complaint as `citizen1` to get complaint ID.
2. Login as `citizen2`.
3. Attempt to open `/user/submitted/<citizen1_complaint_id>` and `/user/submitted/<id>/download/*`.

**Expected Results / Pass Criteria**
- ✅ 403 Forbidden is returned or access is blocked.
- ✅ No letter data or complaint fields are disclosed.

**Actual Feedback**
- Access blocked as expected.

**Verdict**: **PASS**

---

### Session 5 — Admin/Reviewer: Update complaint status + verify history + export
**User**: Agency Reviewer (`reviewer1@test.local`) and Super Admin (`admin@ingat.com`)

**Steps**
1. Login to `/admin/login`.
2. Open `/admin/reports`.
3. Filter by violation type and status.
4. Open complaint detail.
5. Update status (e.g., Submitted → Under Review → Forwarded to Agency → Resolved).
6. Verify status history entries appear.
7. Trigger CSV export.

**Expected Results / Pass Criteria**
- ✅ Status changes are persisted.
- ✅ `StatusHistory` records are created for each transition.
- ✅ CSV export downloads successfully and contains accurate complaint rows.

**Actual Feedback**
- Admin filters work; status detail is correct; CSV export provides expected columns.

**Verdict**: **PASS**

---

## Final Evaluation Summary
### Major Flows
- Complaint submission end-to-end: ✅ PASS
- Voice input: ✅ PASS
- Maps privacy: ✅ PASS
- Gemini letter generation & fallback: ✅ PASS
- Permissions: ✅ PASS
- Admin reporting and exports: ✅ PASS

### Overall UAT Readiness
- **Overall UAT Result**: ✅ READY FOR PANEL DEMO
- **Outstanding Issues**: None blocking (only non-functional warnings and external service availability variability).

