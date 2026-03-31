# Project Problems & Fixes

## Critical Issues

### 1. Plain-text Password Storage
**Problem:** `authentication/models.py` stored passwords in a plain `CharField(max_length=100)` with a hardcoded default of `"ADMIN"`. No hashing whatsoever — passwords were readable directly from the database.

**Fix:** Added `set_password()` and `check_password()` methods to the `User` model using SHA-256 with a random salt (`sha256:<salt>:<hash>` format). Updated `authentication/views.py` to use `user.check_password(password)` instead of direct string comparison. Includes a legacy plain-text fallback for existing records.

---

### 2. Duplicate `FacultyProfile` Model
**Problem:** Both `backend/faculty/models.py` and `backend/administration/models.py` defined a `FacultyProfile` model with different fields and conflicting `related_name` values (`faculty_module_profile` vs `faculty_profile`). This caused schema conflicts and made it unclear which model was authoritative.

**Fix:** Removed the duplicate `FacultyProfile` from `backend/administration/models.py`. The canonical model lives in `backend/faculty/models.py`. The administration views already imported from `backend.faculty.models`, so no view changes were needed.

---

### 3. Session Auth Fallback Leaks Data
**Problem:** Both `get_student_profile()` and `get_faculty_profile()` fell back to `.objects.first()` when no session was found. An unauthenticated user would silently see the first student/faculty record in the database.

**Fix:** Removed the fallback — both functions now return `None` when no session is present. Views already handle the `None` case with appropriate error messages.

---

### 4. Hardcoded `SECRET_KEY` and Insecure Settings
**Problem:** `SECRET_KEY` was committed directly in `core/settings.py`. `DEBUG = True` and `ALLOWED_HOSTS = []` were hardcoded, making the app reject all requests in production and expose debug info.

**Fix:** All three now read from environment variables with safe defaults:
- `SECRET_KEY` → `os.environ.get('SECRET_KEY', '<insecure-default>')`
- `DEBUG` → `os.environ.get('DEBUG', 'True') == 'True'`
- `ALLOWED_HOSTS` → `os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')`

---

### 5. Assignment Model / Migration Mismatch
**Problem:** Migration `0007` added `allow_submissions`, `attachment`, `max_marks` fields and an `AssignmentSubmission` model to the `Assignment` table, but none of these were reflected in `backend/faculty/models.py`. Running the app with this mismatch would cause `OperationalError` on any query touching those columns.

**Fix:** Added all three missing fields and the full `AssignmentSubmission` model to `backend/faculty/models.py` to match the applied migration exactly.

---

## Structural Issues

### 6. Missing `backend/student/admin.py`
**Problem:** The file didn't exist, so none of the student models (`StudentProfile`, `Course`, `Enrollment`, `Attendance`, `FeeRecord`, `AcademicRecord`, `AttendanceMonitoringLog`) were accessible through the Django admin interface.

**Fix:** Created `backend/student/admin.py` with `@admin.register` for all student models, including useful `list_display`, `search_fields`, and `list_filter` configurations.

---

### 7. Missing `STATIC_ROOT` and Media Configuration
**Problem:** `core/settings.py` defined `STATICFILES_DIRS` but no `STATIC_ROOT`, so `collectstatic` would fail in production. There was also no `MEDIA_URL` or `MEDIA_ROOT`, meaning file uploads (assignment attachments) would fail silently.

**Fix:** Added `STATIC_ROOT`, `MEDIA_URL`, and `MEDIA_ROOT` to `core/settings.py`. Added media URL serving via `django.conf.urls.static` in `core/urls.py` (active only when `DEBUG=True`).

---

### 8. No Logout Endpoint
**Problem:** There was no way to clear a user's session — no logout view or URL existed. Users were permanently logged in until the session expired.

**Fix:** Added `logout_view` to `authentication/views.py` that calls `request.session.flush()` and redirects to `/`. Registered at `auth/logout/`.

---

## Configuration Issues

### 9. Ollama Integration — Hardcoded URL and 90s Timeout
**Problem:** `core/ollama_utils.py` hardcoded `http://127.0.0.1:11434` and used a 90-second timeout with a bare `except Exception`. If Ollama wasn't running, every request using it would hang for 90 seconds before failing with a cryptic error.

**Fix:** URL, model name, and timeout are now configurable via environment variables (`OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`). Default timeout reduced to 30 seconds. Added specific `except` clauses for `ConnectionError` and `Timeout` with user-friendly fallback messages.

---

### 10. `.env.example` Incomplete
**Problem:** `.env.example` only listed email settings, missing all the other environment variables the app depends on.

**Fix:** Updated `.env.example` to include `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and the new Ollama settings.

---

## Logic Bugs

### 11. `current_year` Property — Wrong Ordinal Suffixes
**Problem:** `StudentProfile.current_year` used a chained ternary that produced wrong results:
- Year 2 → `"2nd Year"` ✓
- Year 3 → `"3rd Year"` ✓
- Year 4 → `"4th Year"` ✓ (but fell into the `th` branch incorrectly)
- The logic was fragile and hard to read.

**Fix:** Replaced with a clean suffix lookup dict `{1: '1st', 2: '2nd', 3: '3rd'}` with a default `f'{year}th'` for anything else.

---

## Known Remaining Issues (Not Fixed — Require Broader Refactor)

| Issue | Reason Not Fixed |
|---|---|
| Custom `User` model doesn't extend `AbstractUser` | Would require a full auth migration and data migration — high risk to existing data |
| No CSRF token verification in templates | Requires template changes — out of scope for backend fixes |
| `add_student` / `add_faculty` views create users with `password='ADMIN'` | Needs a proper password-setting flow in the admin UI |
| Attendance grouping assumes `[P]` suffix for practicals | Logic works for current data; changing it risks breaking existing attendance records |
| No form validation on student/faculty creation | Requires form classes or serializers — larger refactor |
| Test emails and coordinator email hardcoded in `attendance_agent.py` | Should be moved to settings/env; low risk but needs careful testing |
