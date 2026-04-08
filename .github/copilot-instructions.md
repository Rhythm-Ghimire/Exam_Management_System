# Copilot Instructions for Exam Management System

## Project Overview
Django-based exam management system for organizing exams, seating arrangements, and invigilator assignments. Two user types: **Admin** (staff) and **Student** (regular users with profile).

## Architecture

### Core Models & Data Flow
- **ExamSchedule** groups exams by branch/semester/term (e.g., "BScCSIT Semester 2 Mid Term"). Links to multiple **Exam** records via foreign key.
- **Exam** belongs to ExamSchedule, references **Subject**. Has date/time, spawns **SeatingArrangement** and **InvigilatorAssignment** records.
- **Student** has `is_eligible()` method: requires `fees_paid=True` AND `attendance >= 75.0`.
- **Result** auto-calculates grade in `save()`: A+ (90%), A (80%), B+ (70%), B (60%), C+ (50%), C (40%), F (<40%).

### Authentication & Authorization
- Login enforces `user_type` (admin vs student) with role verification in [views.py](core/views.py#L38-L68).
- Use `@user_passes_test(is_admin)` decorator to protect admin endpoints. `is_admin()` checks `user.is_staff or user.is_superuser`.

## Complex Algorithms

### Seating Arrangement ([seating.py](core/algorithms/seating.py))
- **Single Group** (same branch+semester): 1 student per bench, other seat empty.
- **Mixed Groups** (different branches/semesters): Interleave students from different groups to fill 2 seats per bench.
- **Hall Filling**: Fills one hall completely before moving to next; uses `capacity // 2` to calculate benches.
- Entry point: `generate_seating_arrangement(exam, students, halls)` called from [views.py](core/views.py#L500) on `generate_seating` endpoint.

### Invigilator Assignment ([invigilator.py](core/algorithms/invigilator.py))
- Uses **backtracking algorithm** to ensure:
  - No invigilator assigned twice in same exam.
  - Max 2 duties per day per invigilator (check `assigned_today` dict).
  - Fair distribution across same-day exams.
- Falls back to greedy assignment (round-robin) if backtracking fails.
- Only assigns to halls that have seating arrangements.

## Developer Workflows

### Running & Testing
```bash
python manage.py runserver          # Start dev server (port 8000)
python manage.py migrate            # Apply database migrations
python manage.py seed_students      # Populate 20 students/semester for testing
python manage.py add_bsccsit_subjects  # Load BScCSIT subjects (sem 1-8)
```

### Creating Migrations
```bash
python manage.py makemigrations core
python manage.py migrate
```

## Project-Specific Conventions

1. **Branch/Semester Filtering**: Always use `branch=` and `semester=` in queries; these are immutable student properties used to determine subject eligibility.
2. **Form Patterns**: All CRUD forms inherit from `forms.ModelForm` with explicit `fields` list. Example: [StudentForm](core/forms.py#L23).
3. **PDF Generation**: Use [PDFGenerator](core/utils/pdf_generator.py) class with static methods (`generate_timetable_pdf`, etc.). Returns BytesIO buffer.
4. **Bulk Operations**: Custom management commands in [core/management/commands/](core/management/commands/) handle data seeding; use Django ORM, not raw SQL.
5. **Template Tags**: Custom filters in [templatetags/custom_filters.py](core/templatetags/custom_filters.py) for view logic.

## Cross-Component Communication
- Views orchestrate: fetch eligible students → call `generate_seating_arrangement()` → call `assign_invigilators()` → save to DB.
- Seating/invigilator functions accept QuerySets and hall lists, return boolean success. They create ORM objects directly.
- No direct API endpoints; all flows through Django URLs in [urls.py](core/urls.py).

## Key File References
- **Models**: [core/models.py](core/models.py) — source of truth for data structure.
- **Views**: [core/views.py](core/views.py) (1218 lines) — all request handlers.
- **Algorithms**: [core/algorithms/](core/algorithms/) — seating & invigilator logic.
- **Forms**: [core/forms.py](core/forms.py) — validation & model binding.
- **URLs**: [core/urls.py](core/urls.py) — routing (59 endpoints).
- **Configuration**: [exam_management/settings.py](exam_management/settings.py) — SQLite DB, templates, middleware.
