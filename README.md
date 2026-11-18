# Exam Management System

A Django web application for running university-style examinations: scheduling exams, checking student eligibility, generating hall seating, assigning invigilators, recording results, and exporting PDFs. It has separate **Admin** and **Student** portals.

**Tech stack:** Python, Django 4.2, SQLite, ReportLab (PDF export), HTML/CSS/JavaScript

## Features

**Admin portal**
- Manage students, subjects, exam halls, and invigilators (add, edit, delete).
- Create exam schedules (e.g. "BScCSIT Semester 2 Mid Term") and add exams to them.
- **Eligibility check:** a student is eligible only if fees are paid and attendance is at least 75%.
- **Automatic seating generation** per exam, per schedule, or per exam type (mid-term / final-term).
- **Automatic invigilator assignment** across halls.
- Enter and manage results, with grades calculated automatically.
- Performance analytics dashboard.
- Download seating plans and timetables as PDF.

**Student portal**
- Log in and view personal timetable and seating arrangement.
- View results and personal analytics.
- Download a personal timetable PDF.

## How the main algorithms work

**Seating (`core/algorithms/seating.py`)**
- If all students belong to one branch and semester, they are seated in roll-number order, one student per bench.
- If students come from different branches or semesters, groups are interleaved so neighbouring students are from different groups (two seats per bench).
- One hall is filled completely before moving to the next, using only halls marked as available.

**Invigilator assignment (`core/algorithms/invigilator.py`)**
- Assigns invigilators only to halls that have seating for the exam.
- Uses backtracking to respect the rules: no invigilator assigned twice in the same exam, a maximum of two duties per day, and fair distribution across same-day exams.
- Falls back to a round-robin assignment if backtracking finds no solution.

**Grading (`core/models.py`)**

| Percentage | Grade |
|---|---|
| 90+ | A+ |
| 80+ | A |
| 70+ | B+ |
| 60+ | B |
| 50+ | C+ |
| 40+ | C |
| below 40 | F |

## Project structure

```
exam_management/        Django project settings and root URLs
core/
├── models.py           Student, Subject, ExamHall, Invigilator, ExamSchedule,
│                       Exam, SeatingArrangement, InvigilatorAssignment, Result
├── views.py            Request handlers for admin and student flows
├── forms.py            ModelForms for all CRUD pages
├── algorithms/         seating.py, invigilator.py
├── utils/              pdf_generator.py (timetable and seating PDFs)
├── management/commands/  seed_students, add_bsccsit_subjects,
│                         add_bca_subjects, generate_random_results
└── templatetags/       custom_filters.py
templates/              HTML templates (dashboards, CRUD pages, seating, analytics)
```

## Getting started

```bash
git clone https://github.com/Rhythm-Ghimire/Exam_Management_System.git
cd Exam_Management_System

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser  # your admin account
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

### Loading demo data

```bash
python manage.py add_bsccsit_subjects   # BSc CSIT subjects, semesters 1-8
python manage.py add_bca_subjects       # BCA subjects
python manage.py seed_students          # sample students for testing
python manage.py generate_random_results
```

## Notes

- The login page checks the selected role (admin or student) against the account type.
- Admin-only pages are protected with Django's `user_passes_test`.
- Seating and invigilator data are stored as normal database rows, so they can be viewed and exported at any time.

## Possible improvements

- Add automated tests for the seating and invigilator algorithms.
- Move secrets and `DEBUG` into environment variables before deploying.
- Support more branches beyond BSc CSIT and BCA.

## Author

**Rhythm Kashyap Ghimire**
[GitHub](https://github.com/Rhythm-Ghimire) · [LinkedIn](https://linkedin.com/in/rhythm-ghimire-6934452a7)
