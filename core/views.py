from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import JsonResponse, HttpResponse
from collections import defaultdict  
from .models import Student, Subject, ExamHall, Invigilator, ExamSchedule, Exam, SeatingArrangement, InvigilatorAssignment, Result
from .forms import StudentRegistrationForm, StudentForm, SubjectForm, ExamHallForm, InvigilatorForm, ExamForm, ResultForm
from .algorithms.seating import generate_seating_arrangement
from .algorithms.invigilator import assign_invigilators
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import json


def is_admin(user):
    return user.is_staff or user.is_superuser


def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is admin (staff or superuser)
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f'Welcome Admin {user.get_full_name() or user.username}!')
                return redirect('dashboard')
            else:
                # Check if student profile exists
                try:
                    student = Student.objects.get(user=user)
                    login(request, user)
                    messages.success(request, f'Welcome {user.get_full_name() or user.username}!')
                    return redirect('dashboard')
                except Student.DoesNotExist:
                    messages.error(request, 'Student profile not found. Please contact admin.')
        else:
            messages.error(request, 'Invalid username or password. Please check your credentials.')
    
    return render(request, 'login.html')


def user_signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'signup.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if request.user.is_staff:
        context = {
            'total_students': Student.objects.count(),
            'total_subjects': Subject.objects.count(),
            'total_exams': Exam.objects.count(),
            'total_halls': ExamHall.objects.count(),
            'eligible_students': Student.objects.filter(fees_paid=True, attendance__gte=75).count(),
            'paid_fees_students': Student.objects.filter(fees_paid=True).count(),
            'unpaid_fees_students': Student.objects.filter(fees_paid=False).count(),
            'upcoming_exams': Exam.objects.select_related('schedule', 'subject').order_by('date')[:5]
        }
        return render(request, 'admin_dashboard.html', context)
    else:
        try:
            from datetime import date
            
            student = Student.objects.get(user=request.user)
            seating = SeatingArrangement.objects.filter(student=student).select_related('exam', 'hall', 'exam__schedule')
            
            # Get ACTIVE schedules only (end_date >= today)
            today = date.today()

            # Find the most recent active schedule for this student's branch+semester
            active_schedule = ExamSchedule.objects.filter(
                semester=student.semester,
                branch=student.branch,
                end_date__gte=today
            ).order_by('-start_date').first()

            # Get upcoming exams from active schedule
            upcoming_exams = []
            if active_schedule:
                upcoming_exams = Exam.objects.filter(
                    schedule=active_schedule,
                    date__gte=today
                ).select_related('schedule', 'subject').order_by('date', 'start_time')

            # seating_arrangements: ONLY from active schedule exams so first_seat
            # always points to the correct current exam (not an old one)
            if active_schedule:
                seating = SeatingArrangement.objects.filter(
                    student=student,
                    exam__schedule=active_schedule
                ).select_related('exam', 'hall', 'exam__schedule').order_by('exam__date')
            else:
                seating = SeatingArrangement.objects.none()
            
            # Get results grouped by schedule
            results_by_schedule = []
            schedules_with_results = ExamSchedule.objects.filter(
                semester=student.semester,
                branch=student.branch,
                exams__result__student=student
            ).distinct().order_by('-created_at')
            
            for schedule in schedules_with_results:
                results = Result.objects.filter(
                    student=student,
                    exam__schedule=schedule
                ).select_related('subject', 'exam')
                
                if results.exists():
                    total_marks = sum(r.marks_obtained for r in results)
                    total_max = sum(r.max_marks for r in results)
                    percentage = (total_marks / total_max * 100) if total_max > 0 else 0
                    
                    passed = results.filter(marks_obtained__gte=40).count()
                    failed = results.count() - passed
                    
                    results_by_schedule.append({
                        'schedule': schedule,
                        'results': results,
                        'percentage': round(percentage, 2),
                        'passed': passed,
                        'failed': failed
                    })
            
            context = {
                'student': student,
                'seating_arrangements': seating,
                'active_schedule': active_schedule,
                'upcoming_exams': upcoming_exams,
                'results_by_schedule': results_by_schedule
            }
            return render(request, 'student_dashboard.html', context)
        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found. Please contact admin.')
            return redirect('index')

@login_required
@user_passes_test(is_admin)
def students_overview(request):
    """Show all students grouped by branch and semester with filtering"""
    # Get filter parameters
    selected_branch = request.GET.get('branch', 'all')
    selected_semester = request.GET.get('semester', 'all')
    
    # Base query
    students = Student.objects.all().select_related('user')
    
    # Apply filters
    if selected_branch != 'all':
        students = students.filter(branch=selected_branch)
    
    if selected_semester != 'all':
        students = students.filter(semester=int(selected_semester))
    
    students = students.order_by('branch', 'semester', 'roll_number')
    
    # Group students by branch and semester
    grouped_students = {}
    for student in students:
        branch = student.branch
        semester = student.semester
        
        if branch not in grouped_students:
            grouped_students[branch] = {}
        
        if semester not in grouped_students[branch]:
            grouped_students[branch][semester] = []
        
        grouped_students[branch][semester].append(student)
    
    # Get subjects and exams by semester
    subjects_by_semester = {}
    exams_by_semester = {}
    
    for semester in range(1, 9):
        subjects_by_semester[semester] = Subject.objects.filter(semester=semester)
        exams_by_semester[semester] = Exam.objects.filter(
            schedule__semester=semester
        ).select_related('subject', 'schedule')
    
    # Available branches and semesters for dropdown
    branches = [('all', 'All Branches'), ('BScCSIT', 'BScCSIT'), ('BCA', 'BCA')]
    semesters = [('all', 'All Semesters')] + [(str(i), f'Semester {i}') for i in range(1, 9)]
    
    context = {
        'grouped_students': grouped_students,
        'subjects_by_semester': subjects_by_semester,
        'exams_by_semester': exams_by_semester,
        'total_students': students.count(),
        'paid_fees': students.filter(fees_paid=True).count(),
        'unpaid_fees': students.filter(fees_paid=False).count(),
        'branches': branches,
        'semesters': semesters,
        'selected_branch': selected_branch,
        'selected_semester': selected_semester,
    }
    
    return render(request, 'students_overview.html', context)


@login_required
@user_passes_test(is_admin)
def manage_students(request):
    """Manage students with filtering"""
    # Get filter parameters
    selected_branch = request.GET.get('branch', 'all')
    selected_semester = request.GET.get('semester', 'all')
    
    # Base query
    students = Student.objects.all().select_related('user')
    
    # Apply filters
    if selected_branch != 'all':
        students = students.filter(branch=selected_branch)
    
    if selected_semester != 'all':
        students = students.filter(semester=int(selected_semester))
    
    students = students.order_by('branch', 'semester', 'roll_number')
    
    # Available branches and semesters for dropdown
    branches = [('all', 'All Branches'), ('BScCSIT', 'BScCSIT'), ('BCA', 'BCA')]
    semesters = [('all', 'All Semesters')] + [(str(i), f'Semester {i}') for i in range(1, 9)]
    
    context = {
        'students': students,
        'branches': branches,
        'semesters': semesters,
        'selected_branch': selected_branch,
        'selected_semester': selected_semester,
    }
    
    return render(request, 'manage_students.html', context)


@login_required
@user_passes_test(is_admin)
def add_student(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        roll_number = request.POST.get('roll_number')
        branch = request.POST.get('branch')
        semester = request.POST.get('semester')
        fees_paid = request.POST.get('fees_paid') == 'on'
        attendance = request.POST.get('attendance')
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            user.is_staff = False  # Important: Students are NOT staff
            user.save()
            
            Student.objects.create(
                user=user,
                roll_number=roll_number,
                branch=branch,
                semester=int(semester),
                fees_paid=fees_paid,
                attendance=float(attendance)
            )
            
            messages.success(request, f'Student {username} added successfully! Password: {password}')
            return redirect('manage_students')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'add_student.html')


@login_required
@user_passes_test(is_admin)
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        student.roll_number = request.POST.get('roll_number')
        student.branch = request.POST.get('branch')
        student.semester = int(request.POST.get('semester'))
        student.fees_paid = request.POST.get('fees_paid') == 'on'
        student.attendance = float(request.POST.get('attendance'))
        
        student.user.first_name = request.POST.get('first_name')
        student.user.last_name = request.POST.get('last_name')
        student.user.email = request.POST.get('email')
        
        student.save()
        student.user.save()
        
        messages.success(request, 'Student updated successfully!')
        return redirect('manage_students')
    
    return render(request, 'edit_student.html', {'student': student})


@login_required
@user_passes_test(is_admin)
def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    user = student.user
    student.delete()
    user.delete()
    messages.success(request, 'Student deleted successfully!')
    return redirect('manage_students')


@login_required
@user_passes_test(is_admin)
def manage_subjects(request):
    """Manage subjects with filtering"""
    # Get filter parameters
    selected_branch = request.GET.get('branch', 'all')
    selected_semester = request.GET.get('semester', 'all')
    
    # Get subjects grouped by branch and semester
    bsccsit_subjects = {}
    bca_subjects = {}
    
    for sem in range(1, 9):
        # Apply semester filter
        if selected_semester != 'all' and int(selected_semester) != sem:
            continue
            
        bsccsit_subjects[sem] = Subject.objects.filter(
            branch='BScCSIT',
            semester=sem
        ).order_by('code')
        
        bca_subjects[sem] = Subject.objects.filter(
            branch='BCA',
            semester=sem
        ).order_by('code')
    
    # Available branches and semesters for dropdown
    branches = [('all', 'All Branches'), ('BScCSIT', 'BScCSIT'), ('BCA', 'BCA')]
    semesters = [('all', 'All Semesters')] + [(str(i), f'Semester {i}') for i in range(1, 9)]
    
    context = {
        'bsccsit_subjects': bsccsit_subjects if selected_branch in ['all', 'BScCSIT'] else {},
        'bca_subjects': bca_subjects if selected_branch in ['all', 'BCA'] else {},
        'branches': branches,
        'semesters': semesters,
        'selected_branch': selected_branch,
        'selected_semester': selected_semester,
    }
    
    return render(request, 'manage_subjects.html', context)


@login_required
@user_passes_test(is_admin)
def add_subject(request):
    if request.method == 'POST':
        Subject.objects.create(
            code=request.POST.get('code'),
            name=request.POST.get('name'),
            semester=int(request.POST.get('semester')),
            branch=request.POST.get('branch')
        )
        messages.success(request, 'Subject added successfully!')
        return redirect('manage_subjects')
    
    return render(request, 'add_subject.html')


@login_required
@user_passes_test(is_admin)
def manage_halls(request):
    halls = ExamHall.objects.all()
    return render(request, 'manage_halls.html', {'halls': halls})


@login_required
@user_passes_test(is_admin)
def add_hall(request):
    if request.method == 'POST':
        ExamHall.objects.create(
            name=request.POST.get('name'),
            capacity=int(request.POST.get('capacity')),
            is_available=request.POST.get('is_available') == 'on'
        )
        messages.success(request, 'Exam hall added successfully!')
        return redirect('manage_halls')
    
    return render(request, 'add_hall.html')


@login_required
@user_passes_test(is_admin)
def manage_invigilators(request):
    invigilators = Invigilator.objects.all()
    return render(request, 'manage_invigilators.html', {'invigilators': invigilators})


@login_required
@user_passes_test(is_admin)
def add_invigilator(request):
    if request.method == 'POST':
        Invigilator.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone')
        )
        messages.success(request, 'Invigilator added successfully!')
        return redirect('manage_invigilators')
    
    return render(request, 'add_invigilator.html')


@login_required
@user_passes_test(is_admin)
def manage_exams(request):
    schedules = ExamSchedule.objects.all().prefetch_related('exams__subject').order_by('branch', 'semester')

    mid_term_schedules = [s for s in schedules if s.exam_type == 'mid_term']
    final_term_schedules = [s for s in schedules if s.exam_type == 'final_term']

    def seating_generated(sched_list):
        for s in sched_list:
            first = s.exams.first()
            if first and first.seatingarrangement_set.exists():
                return True
        return False

    mid_seating_done = seating_generated(mid_term_schedules)
    final_seating_done = seating_generated(final_term_schedules)

    return render(request, 'manage_exams.html', {
        'mid_term_schedules': mid_term_schedules,
        'final_term_schedules': final_term_schedules,
        'mid_seating_done': mid_seating_done,
        'final_seating_done': final_seating_done,
    })


@login_required
@user_passes_test(is_admin)
def create_exam_schedule(request):
    """Step 1: Create exam schedule (branch, semester, exam type)"""
    if request.method == 'POST':
        branch = request.POST.get('branch')
        semester = int(request.POST.get('semester'))
        exam_type = request.POST.get('exam_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # Create schedule name
        exam_type_display = 'Mid Term' if exam_type == 'mid_term' else 'Final Term'
        schedule_name = f"{branch} Semester {semester} {exam_type_display} {start_date[:4]}"
        
        # Check if schedule already exists
        existing = ExamSchedule.objects.filter(
            branch=branch,
            semester=semester,
            exam_type=exam_type,
            start_date=start_date
        ).first()
        
        if existing:
            messages.info(request, f'Schedule already exists: {existing.name}')
            return redirect('add_exam_to_schedule', schedule_id=existing.id)
        
        # Create new schedule
        schedule = ExamSchedule.objects.create(
            name=schedule_name,
            branch=branch,
            semester=semester,
            exam_type=exam_type,
            start_date=start_date,
            end_date=end_date
        )
        
        messages.success(request, f'Schedule created: {schedule_name}. Now add exams to this schedule.')
        return redirect('add_exam_to_schedule', schedule_id=schedule.id)
    
    return render(request, 'create_exam_schedule.html')


@login_required
@user_passes_test(is_admin)
def add_exam_to_schedule(request, schedule_id):
    """Step 2: Add exams to the schedule"""
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        subject = Subject.objects.get(id=subject_id)
        
        # Check if exam already exists for this subject in this schedule
        existing = Exam.objects.filter(schedule=schedule, subject=subject).first()
        if existing:
            messages.warning(request, f'Exam for {subject.name} already exists in this schedule.')
        else:
            Exam.objects.create(
                schedule=schedule,
                subject=subject,
                date=date,
                start_time=start_time,
                end_time=end_time
            )
            messages.success(request, f'Added exam for {subject.name}')
        
        # Check if user wants to add more
        if request.POST.get('add_another'):
            return redirect('add_exam_to_schedule', schedule_id=schedule.id)
        else:
            return redirect('manage_exams')
    
    # Get subjects for this branch and semester
    subjects = Subject.objects.filter(
        branch=schedule.branch,
        semester=schedule.semester
    ).order_by('code')
    
    # Get already added exams
    added_exams = schedule.exams.all().select_related('subject')
    added_subject_ids = [exam.subject.id for exam in added_exams]
    
    context = {
        'schedule': schedule,
        'subjects': subjects,
        'added_exams': added_exams,
        'added_subject_ids': added_subject_ids,
    }
    
    return render(request, 'add_exam_to_schedule.html', context)


@login_required
@user_passes_test(is_admin)
def generate_seating(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Clear existing seating and invigilator assignments
    SeatingArrangement.objects.filter(exam=exam).delete()
    InvigilatorAssignment.objects.filter(exam=exam).delete()
    
    # Get semester from schedule
    semester = exam.schedule.semester if exam.schedule else exam.subject.semester
    
    # Get eligible students
    students = Student.objects.filter(
        semester=semester,
        fees_paid=True,
        attendance__gte=75.0
    ).order_by('roll_number')
    
    if not students.exists():
        messages.error(request, 'No eligible students found for this exam.')
        return redirect('manage_exams')
    
    # Get available halls
    halls = ExamHall.objects.filter(is_available=True).order_by('-capacity')
    
    if not halls.exists():
        messages.error(request, 'No available exam halls found.')
        return redirect('manage_exams')
    
    # Generate seating arrangement
    success = generate_seating_arrangement(exam, students, halls)
    
    if not success:
        messages.error(request, 'Failed to generate seating arrangement. Insufficient capacity.')
        return redirect('manage_exams')
    
    # Assign invigilators
    invigilators = Invigilator.objects.all()
    
    if invigilators.exists():
        assign_invigilators(exam, halls, invigilators)
    
    messages.success(request, 'Seating arrangement and invigilator assignment generated successfully!')
    return redirect('view_seating', exam_id=exam.id)


@login_required
@user_passes_test(is_admin)
def generate_schedule_seating(request, schedule_id):
    """Legacy: generate seating for a single schedule (redirects to exam-type generator)"""
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    return redirect('generate_seating_by_examtype', exam_type=schedule.exam_type)


def _build_seating_for_date(date_exams, available_halls):
    """
    Core seating algorithm for all exams happening on the SAME date.

    Rules:
    - Each hall has capacity C → n = C//2 benches.
    - If only ONE group (branch+semester) has exams that day:
        one student per bench (anti-cheat), fill hall completely then move to next.
    - If MULTIPLE groups have exams that day:
        interleave groups round-robin (Sem3, Sem4, Sem3, Sem4...) so bench
        partners are always from different semesters/branches.
    - Fill each hall completely before moving to the next.

    Returns: (seating_plan, overflow_occurred)
      seating_plan = list of {student, hall, bench}
    """
    # Collect unique student groups for this date
    group_map = {}   # (branch, semester) → [students]
    for exam in date_exams:
        key = (exam.schedule.branch, exam.schedule.semester)
        if key not in group_map:
            group_map[key] = list(
                Student.objects.filter(
                    branch=exam.schedule.branch,
                    semester=exam.schedule.semester
                ).order_by('roll_number')
            )

    groups = list(group_map.values())
    num_groups = len(groups)

    if num_groups == 0:
        return [], False

    if num_groups == 1:
        # Single group → one student per bench (no pairing, anti-cheat)
        student_sequence = [(s, False) for s in groups[0]]
    else:
        # Multiple groups → interleave round-robin
        max_len = max(len(g) for g in groups)
        interleaved = []
        for i in range(max_len):
            for g in groups:
                if i < len(g):
                    interleaved.append(g[i])
        student_sequence = [(s, True) for s in interleaved]

    # Assign to halls — fill each hall completely before moving on
    seating_plan = []
    halls_list = list(available_halls)
    hall_idx = 0
    stu_idx = 0
    total = len(student_sequence)

    while stu_idx < total and hall_idx < len(halls_list):
        hall = halls_list[hall_idx]
        num_benches = hall.capacity // 2

        for bench in range(1, num_benches + 1):
            if stu_idx >= total:
                break

            student1, can_pair = student_sequence[stu_idx]
            seating_plan.append({'student': student1, 'hall': hall, 'bench': bench})
            stu_idx += 1

            if can_pair and stu_idx < total:
                student2, _ = student_sequence[stu_idx]
                diff_group = (student1.branch != student2.branch or
                              student1.semester != student2.semester)
                if diff_group:
                    seating_plan.append({'student': student2, 'hall': hall, 'bench': bench})
                    stu_idx += 1

        hall_idx += 1

    return seating_plan, (stu_idx < total)


@login_required
@user_passes_test(is_admin)
def generate_seating_by_examtype(request, exam_type):
    """
    Master seating generator for all schedules of a given exam_type.

    Key insight: when Sem3 and Sem4 share the same date, they produce ONE
    combined seating plan (interleaved). Every exam on that date — whether
    it belongs to Sem3 or Sem4 — gets the FULL combined seating record so
    that viewing either exam shows the same hall layout with both groups.
    """
    schedules = ExamSchedule.objects.filter(exam_type=exam_type).prefetch_related('exams')

    if not schedules.exists():
        messages.error(request, f'No {exam_type.replace("_", " ").title()} schedules found.')
        return redirect('manage_exams')

    all_exams = Exam.objects.filter(
        schedule__exam_type=exam_type
    ).select_related('schedule', 'subject').order_by('date', 'start_time')

    if not all_exams.exists():
        messages.error(request, 'No exams found in these schedules.')
        return redirect('manage_exams')

    # Clear existing seating and invigilator assignments
    for exam in all_exams:
        SeatingArrangement.objects.filter(exam=exam).delete()
        InvigilatorAssignment.objects.filter(exam=exam).delete()

    available_halls = ExamHall.objects.filter(is_available=True).order_by('name')
    if not available_halls.exists():
        messages.error(request, 'No available exam halls found.')
        return redirect('manage_exams')

    invigilators = Invigilator.objects.all()

    # Group all exams by date
    exams_by_date = defaultdict(list)
    for exam in all_exams:
        exams_by_date[exam.date].append(exam)

    total_seated = 0
    overflow_dates = []

    for exam_date, date_exams in sorted(exams_by_date.items()):
        seating_plan, overflow = _build_seating_for_date(date_exams, available_halls)

        if overflow:
            overflow_dates.append(str(exam_date))

        # Build lookup: student → their own exam on this date
        # (each student belongs to exactly one exam on a given date)
        student_to_exam = {}
        for exam in date_exams:
            for student in Student.objects.filter(
                branch=exam.schedule.branch,
                semester=exam.schedule.semester
            ):
                student_to_exam[student.id] = exam

        # Save SeatingArrangement for each student using their own exam.
        # ALSO save a cross-reference record for every OTHER exam on this
        # date so that viewing any exam on that date shows the full
        # combined hall layout.
        for seat_info in seating_plan:
            student = seat_info['student']
            hall    = seat_info['hall']
            bench   = seat_info['bench']

            own_exam = student_to_exam.get(student.id)
            if not own_exam:
                continue

            # Primary record: student ↔ their own exam
            SeatingArrangement.objects.get_or_create(
                exam=own_exam,
                student=student,
                defaults={'hall': hall, 'seat_number': bench}
            )
            total_seated += 1

            # Cross-reference: also save this student's seat against every
            # OTHER exam on this date so the hall view is complete for all.
            for other_exam in date_exams:
                if other_exam.id == own_exam.id:
                    continue
                SeatingArrangement.objects.get_or_create(
                    exam=other_exam,
                    student=student,
                    defaults={'hall': hall, 'seat_number': bench}
                )

        # Assign invigilators once per exam on this date
        if invigilators.exists():
            halls_used_ids = SeatingArrangement.objects.filter(
                exam__in=date_exams
            ).values_list('hall', flat=True).distinct()
            halls_used = ExamHall.objects.filter(id__in=halls_used_ids).order_by('name')
            for exam in date_exams:
                assign_invigilators(exam, halls_used, invigilators)

    if overflow_dates:
        messages.warning(request,
            f'⚠️ Not enough hall capacity on: {", ".join(overflow_dates)}. Some students may not have seats.')
    else:
        messages.success(request,
            f'✅ Seating generated across all {exam_type.replace("_", " ").title()} schedules!')

    return redirect('manage_exams')

@login_required
def view_seating(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Build halls_data identically for both admin and student
    all_seating = SeatingArrangement.objects.filter(exam=exam).select_related(
        'student', 'hall', 'student__user'
    ).order_by('hall__name', 'seat_number', 'id')
    invigilators = InvigilatorAssignment.objects.filter(exam=exam).select_related('invigilator', 'hall')

    halls_data = {}
    for seat in all_seating:
        hname = seat.hall.name
        if hname not in halls_data:
            halls_data[hname] = {'benches': {}, 'total_students': 0, 'hall_obj': seat.hall}
        bn = seat.seat_number
        if bn not in halls_data[hname]['benches']:
            halls_data[hname]['benches'][bn] = []
        halls_data[hname]['benches'][bn].append(seat)
        halls_data[hname]['total_students'] += 1

    if request.user.is_staff:
        context = {
            'exam': exam,
            'halls_data': halls_data,
            'invigilators': invigilators,
        }
        return render(request, 'view_seating.html', context)
    else:
        try:
            student = Student.objects.get(user=request.user)
            my_seating = SeatingArrangement.objects.filter(exam=exam, student=student).first()
            context = {
                'exam': exam,
                'halls_data': halls_data,
                'invigilators': invigilators,
                'my_seating': my_seating,
                'my_roll': student.roll_number,
            }
            return render(request, 'student_seating.html', context)
        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found.')
            return redirect('dashboard')

@login_required
def download_seating_pdf(request, exam_id):
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.pdfgen import canvas as pdf_canvas

    exam = get_object_or_404(Exam, id=exam_id)
    all_seating = SeatingArrangement.objects.filter(exam=exam).select_related(
        'student', 'hall', 'student__user'
    ).order_by('hall__name', 'seat_number', 'id')
    invigilators = InvigilatorAssignment.objects.filter(exam=exam).select_related('invigilator', 'hall')

    # Identify requesting student for seat highlight
    my_roll = None
    if not request.user.is_staff:
        try:
            my_roll = Student.objects.get(user=request.user).roll_number
        except Student.DoesNotExist:
            pass

    # Group by hall -> bench -> [seat1, seat2]
    halls_data = {}
    for seat in all_seating:
        hname = seat.hall.name
        if hname not in halls_data:
            halls_data[hname] = {'benches': {}, 'total': 0}
        bn = seat.seat_number
        if bn not in halls_data[hname]['benches']:
            halls_data[hname]['benches'][bn] = []
        halls_data[hname]['benches'][bn].append(seat)
        halls_data[hname]['total'] += 1

    buffer = BytesIO()
    PAGE_W, PAGE_H = landscape(A4)
    c = pdf_canvas.Canvas(buffer, pagesize=landscape(A4))

    MARGIN   = 36
    HEADER_H = 72
    FOOTER_H = 25
    COL_GAP  = 28       # gap between left and right column-groups
    DIV_W    = 20       # bench-number strip width
    BENCH_H  = 44       # height of one bench row
    BENCH_GAP= 5        # vertical gap between rows

    USABLE_W  = PAGE_W - 2 * MARGIN
    GROUP_W   = (USABLE_W - COL_GAP) / 2
    SEAT_W    = (GROUP_W - DIV_W) / 2

    USABLE_H      = PAGE_H - HEADER_H - FOOTER_H - MARGIN
    ROWS_PER_PAGE = int(USABLE_H / (BENCH_H + BENCH_GAP))

    def page_header(hall_name, inv_name):
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(PAGE_W / 2, PAGE_H - 28, hall_name)
        c.setFont("Helvetica", 9)
        c.drawCentredString(PAGE_W / 2, PAGE_H - 44,
                            f"{exam.subject.name}  —  {exam.date.strftime('%Y-%m-%d')}")
        if inv_name:
            c.setFont("Helvetica-Oblique", 8)
            c.drawRightString(PAGE_W - MARGIN, PAGE_H - 28, f"Invigilator: {inv_name}")
        c.setLineWidth(0.7)
        c.line(MARGIN, PAGE_H - HEADER_H, PAGE_W - MARGIN, PAGE_H - HEADER_H)

    def bench_row(gx, y, bench_num, seats_in_bench):
        """Draw one bench row: [left seat | divider | right seat]"""
        total_w = GROUP_W
        c.setLineWidth(0.5)
        c.rect(gx, y - BENCH_H, total_w, BENCH_H, stroke=1, fill=0)

        # Grey divider strip
        c.setFillColorRGB(0.88, 0.88, 0.88)
        c.rect(gx + SEAT_W, y - BENCH_H, DIV_W, BENCH_H, stroke=0, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.setLineWidth(0.3)
        c.line(gx + SEAT_W,         y, gx + SEAT_W,         y - BENCH_H)
        c.line(gx + SEAT_W + DIV_W, y, gx + SEAT_W + DIV_W, y - BENCH_H)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawCentredString(gx + SEAT_W + DIV_W / 2, y - BENCH_H / 2 - 3, str(bench_num))
        c.setFillColorRGB(0, 0, 0)

        seat_x_list = [gx, gx + SEAT_W + DIV_W]
        for idx, sx in enumerate(seat_x_list):
            if idx >= len(seats_in_bench):
                break
            seat = seats_in_bench[idx]
            is_me = (my_roll and seat.student.roll_number == my_roll)
            is_ineligible = not seat.student.is_eligible()

            if is_me:
                c.setFillColorRGB(1.0, 0.96, 0.5)
                c.rect(sx, y - BENCH_H, SEAT_W, BENCH_H, stroke=0, fill=1)
                c.setFillColorRGB(0, 0, 0)

            if is_ineligible:
                c.setFillColorRGB(0.75, 0.1, 0.1)

            name = seat.student.user.get_full_name() or seat.student.roll_number
            if len(name) > 20: name = name[:18] + "…"
            c.setFont("Helvetica-Bold", 8)
            c.drawString(sx + 4, y - 16, name)
            c.setFont("Helvetica", 7)
            c.drawString(sx + 4, y - 27, seat.student.roll_number)
            if is_ineligible:
                c.setFont("Helvetica-Oblique", 6)
                c.drawString(sx + 4, y - 37, "(Ineligible)")
            c.setFillColorRGB(0, 0, 0)

    for hall_name, hdata in halls_data.items():
        inv_obj  = invigilators.filter(hall__name=hall_name).first()
        inv_name = inv_obj.invigilator.name if inv_obj else ""

        bench_numbers = sorted(hdata['benches'].keys())
        total = len(bench_numbers)
        mid   = (total + 1) // 2
        left_col  = bench_numbers[:mid]
        right_col = bench_numbers[mid:]

        for page_start in range(0, max(len(left_col), 1), ROWS_PER_PAGE):
            left_chunk  = left_col[page_start : page_start + ROWS_PER_PAGE]
            right_chunk = right_col[page_start : page_start + ROWS_PER_PAGE]

            page_header(hall_name, inv_name)

            left_gx  = MARGIN
            right_gx = MARGIN + GROUP_W + COL_GAP
            top_y    = PAGE_H - HEADER_H - BENCH_GAP

            for row_i, bn in enumerate(left_chunk):
                y = top_y - row_i * (BENCH_H + BENCH_GAP)
                bench_row(left_gx, y, bn, hdata['benches'].get(bn, []))

            for row_i, bn in enumerate(right_chunk):
                y = top_y - row_i * (BENCH_H + BENCH_GAP)
                bench_row(right_gx, y, bn, hdata['benches'].get(bn, []))

            c.setFont("Helvetica", 8)
            c.drawString(MARGIN, FOOTER_H, f"Total students: {hdata['total']}")
            c.drawRightString(PAGE_W - MARGIN, FOOTER_H, f"Generated: {exam.date}")
            c.showPage()

    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="seating_{exam.subject.code}_{exam.date}.pdf"'
    )
    return response

@login_required
@user_passes_test(is_admin)
def manage_results(request):
    """Manage results with filtering"""
    # Get filter parameters
    selected_branch = request.GET.get('branch', 'all')
    selected_semester = request.GET.get('semester', 'all')
    
    # Base query
    results = Result.objects.all().select_related('student', 'subject', 'exam')
    
    # Apply filters
    if selected_branch != 'all':
        results = results.filter(student__branch=selected_branch)
    
    if selected_semester != 'all':
        results = results.filter(student__semester=int(selected_semester))
    
    results = results.order_by('student__branch', 'student__semester', 'student__roll_number')
    
    # Available branches and semesters for dropdown
    branches = [('all', 'All Branches'), ('BScCSIT', 'BScCSIT'), ('BCA', 'BCA')]
    semesters = [('all', 'All Semesters')] + [(str(i), f'Semester {i}') for i in range(1, 9)]
    
    context = {
        'results': results,
        'branches': branches,
        'semesters': semesters,
        'selected_branch': selected_branch,
        'selected_semester': selected_semester,
    }
    
    return render(request, 'manage_results.html', context)


@login_required
@user_passes_test(is_admin)
def add_result(request):
    if request.method == 'POST':
        student = Student.objects.get(id=request.POST.get('student'))
        subject = Subject.objects.get(id=request.POST.get('subject'))
        exam = Exam.objects.get(id=request.POST.get('exam'))
        
        Result.objects.create(
            student=student,
            subject=subject,
            exam=exam,
            marks_obtained=float(request.POST.get('marks_obtained')),
            max_marks=float(request.POST.get('max_marks', 100))
        )
        
        messages.success(request, 'Result added successfully!')
        return redirect('manage_results')
    
    students = Student.objects.all()
    subjects = Subject.objects.all()
    exams = Exam.objects.all()
    
    return render(request, 'add_result.html', {
        'students': students,
        'subjects': subjects,
        'exams': exams
    })


@login_required
def performance_analytics(request):
    if request.user.is_staff:
        # Get filter parameters
        selected_branch = request.GET.get('branch', 'all')
        selected_semester = request.GET.get('semester', 'all')
        
        # Get subjects based on filters
        subjects = Subject.objects.all()
        
        if selected_branch != 'all':
            subjects = subjects.filter(branch=selected_branch)
        
        if selected_semester != 'all':
            subjects = subjects.filter(semester=int(selected_semester))
        
        analytics_data = []
        
        for subject in subjects:
            results = Result.objects.filter(subject=subject)
            total = results.count()
            
            if total > 0:
                passed = results.filter(marks_obtained__gte=40).count()
                failed = total - passed
                avg_marks = results.aggregate(Avg('marks_obtained'))['marks_obtained__avg']
                
                analytics_data.append({
                    'subject': subject.name,
                    'code': subject.code,
                    'branch': subject.branch,
                    'semester': subject.semester,
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'pass_percentage': round((passed / total) * 100, 2),
                    'avg_marks': round(avg_marks, 2) if avg_marks else 0
                })
        
        # Available branches and semesters for dropdown
        branches = [('all', 'All Branches'), ('BScCSIT', 'BScCSIT'), ('BCA', 'BCA')]
        semesters = [('all', 'All Semesters')] + [(str(i), f'Semester {i}') for i in range(1, 9)]
        
        context = {
            'analytics_data': analytics_data,
            'branches': branches,
            'semesters': semesters,
            'selected_branch': selected_branch,
            'selected_semester': selected_semester,
        }
        return render(request, 'admin_analytics.html', context)
    else:
        # Student analytics
        try:
            student = Student.objects.get(user=request.user)
            results = Result.objects.filter(student=student).select_related('subject')
            
            total_marks = 0
            total_max = 0
            subject_performance = []
            
            for result in results:
                total_marks += result.marks_obtained
                total_max += result.max_marks
                percentage = (result.marks_obtained / result.max_marks) * 100
                
                subject_performance.append({
                    'subject': result.subject.name,
                    'marks': result.marks_obtained,
                    'max_marks': result.max_marks,
                    'percentage': round(percentage, 2),
                    'grade': result.grade,
                    'status': 'Pass' if result.marks_obtained >= 40 else 'Fail'
                })
            
            overall_percentage = (total_marks / total_max * 100) if total_max > 0 else 0
            
            context = {
                'subject_performance': subject_performance,
                'overall_percentage': round(overall_percentage, 2),
                'total_subjects': len(subject_performance)
            }
            
            return render(request, 'student_analytics.html', context)
        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found.')
            return redirect('dashboard')


@login_required
def timetable(request):
    if request.user.is_staff:
        schedules = ExamSchedule.objects.all().prefetch_related('exams__subject')
    else:
        try:
            student = Student.objects.get(user=request.user)
            schedules = ExamSchedule.objects.filter(
                semester=student.semester,
                branch=student.branch
            ).prefetch_related('exams__subject')
        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found.')
            return redirect('dashboard')
    
    return render(request, 'timetable.html', {'schedules': schedules})


@login_required
def get_subjects_api(request):
    """API endpoint to get subjects by branch and semester"""
    branch = request.GET.get('branch')
    semester = request.GET.get('semester')
    
    if branch and semester:
        subjects = Subject.objects.filter(branch=branch, semester=int(semester)).values('id', 'code', 'name')
        return JsonResponse({'subjects': list(subjects)})
    
    return JsonResponse({'subjects': []})

# Add these new view functions to your views.py

@login_required
@user_passes_test(is_admin)
def edit_hall(request, hall_id):
    hall = get_object_or_404(ExamHall, id=hall_id)
    
    if request.method == 'POST':
        hall.name = request.POST.get('name')
        hall.capacity = int(request.POST.get('capacity'))
        hall.is_available = request.POST.get('is_available') == 'on'
        hall.save()
        
        messages.success(request, f'Hall {hall.name} updated successfully!')
        return redirect('manage_halls')
    
    return render(request, 'edit_hall.html', {'hall': hall})


@login_required
@user_passes_test(is_admin)
def delete_hall(request, hall_id):
    hall = get_object_or_404(ExamHall, id=hall_id)
    hall_name = hall.name
    hall.delete()
    messages.success(request, f'Hall {hall_name} deleted successfully!')
    return redirect('manage_halls')


@login_required
@user_passes_test(is_admin)
def edit_invigilator(request, invigilator_id):
    invigilator = get_object_or_404(Invigilator, id=invigilator_id)
    
    if request.method == 'POST':
        invigilator.name = request.POST.get('name')
        invigilator.email = request.POST.get('email')
        invigilator.phone = request.POST.get('phone')
        invigilator.save()
        
        messages.success(request, f'Invigilator {invigilator.name} updated successfully!')
        return redirect('manage_invigilators')
    
    return render(request, 'edit_invigilator.html', {'invigilator': invigilator})


@login_required
@user_passes_test(is_admin)
def delete_invigilator(request, invigilator_id):
    invigilator = get_object_or_404(Invigilator, id=invigilator_id)
    invigilator_name = invigilator.name
    invigilator.delete()
    messages.success(request, f'Invigilator {invigilator_name} deleted successfully!')
    return redirect('manage_invigilators')


@login_required
@user_passes_test(is_admin)
def edit_result(request, result_id):
    result = get_object_or_404(Result, id=result_id)
    
    if request.method == 'POST':
        result.marks_obtained = float(request.POST.get('marks_obtained'))
        result.max_marks = float(request.POST.get('max_marks'))
        result.save()  # Grade will be auto-calculated by the model
        
        messages.success(request, 'Result updated successfully!')
        return redirect('manage_results')
    
    students = Student.objects.all()
    subjects = Subject.objects.all()
    exams = Exam.objects.all()
    
    return render(request, 'edit_result.html', {
        'result': result,
        'students': students,
        'subjects': subjects,
        'exams': exams
    })


@login_required
@user_passes_test(is_admin)
def delete_result(request, result_id):
    result = get_object_or_404(Result, id=result_id)
    student_name = result.student.user.get_full_name()
    subject_name = result.subject.name
    result.delete()
    messages.success(request, f'Result for {student_name} in {subject_name} deleted successfully!')
    return redirect('manage_results')


@login_required
@user_passes_test(is_admin)
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    subject_name = exam.subject.name
    exam.delete()
    messages.success(request, f'Exam for {subject_name} deleted successfully!')
    return redirect('manage_exams')


@login_required
@user_passes_test(is_admin)
def delete_schedule(request, schedule_id):
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    schedule_name = schedule.name
    schedule.delete()
    messages.success(request, f'Schedule "{schedule_name}" and all its exams deleted successfully!')
    return redirect('manage_exams')

@login_required
@user_passes_test(is_admin)
def schedule_results(request, schedule_id):
    """View results for entire exam schedule"""
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    exams = schedule.exams.all()
    
    # Get ALL students for this branch/semester (not just those with results)
    students = Student.objects.filter(
        branch=schedule.branch,
        semester=schedule.semester
    ).select_related('user').order_by('roll_number')
    
    # Get results for each student
    students_results = []
    for student in students:
        # Get results for this schedule (exam can be null now)
        results = Result.objects.filter(
            student=student,
            subject__semester=schedule.semester,
            subject__branch=schedule.branch
        ).select_related('subject', 'exam')
        
        if results.exists():
            total_marks = sum(r.marks_obtained for r in results)
            total_max = sum(r.max_marks for r in results)
            percentage = (total_marks / total_max * 100) if total_max > 0 else 0
            
            students_results.append({
                'student': student,
                'results': results,
                'total_marks': total_marks,
                'total_max': total_max,
                'percentage': round(percentage, 2),
                'total_subjects': results.count()
            })
    
    context = {
        'schedule': schedule,
        'students_results': students_results,
        'total_students': students.count()
    }
    
    return render(request, 'schedule_results.html', context)

@login_required
def download_student_timetable(request, student_id):
    from datetime import date
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
    
    student = get_object_or_404(Student, id=student_id)
    
    # Check if this is the logged-in student
    if not request.user.is_staff and student.user != request.user:
        messages.error(request, 'You can only download your own timetable.')
        return redirect('dashboard')
    
    # Get active schedule
    today = date.today()
    active_schedule = ExamSchedule.objects.filter(
        semester=student.semester,
        branch=student.branch,
        end_date__gte=today
    ).order_by('-created_at').first()
    
    if not active_schedule:
        messages.error(request, 'No active exam schedule found.')
        return redirect('dashboard')
    
    # Get exams
    exams = Exam.objects.filter(
        schedule=active_schedule,
        date__gte=today
    ).select_related('subject').order_by('date', 'start_time')
    
    # Get seating info
    seating = SeatingArrangement.objects.filter(
        student=student,
        exam__schedule=active_schedule
    ).select_related('hall').first()
    
    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 50, "Exam Timetable")
    
    # Student Info
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 90, f"Student: {student.user.get_full_name()}")
    c.drawString(50, height - 110, f"Roll No: {student.roll_number}")
    c.drawString(50, height - 130, f"Branch: {student.branch} | Semester: {student.semester}")
    
    # Seating Info
    if seating:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 160, f"Your Seat: Hall {seating.hall.name}, Bench {seating.seat_number}")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 180, "(Same seat for all exams)")
    
    # Line
    c.line(50, height - 200, width - 50, height - 200)
    
    # Schedule Name
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 230, active_schedule.name)
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 250, f"{active_schedule.start_date.strftime('%B %d, %Y')} - {active_schedule.end_date.strftime('%B %d, %Y')}")
    
    # Exam Schedule
    y_position = height - 290
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_position, "Date")
    c.drawString(150, y_position, "Day")
    c.drawString(220, y_position, "Subject")
    c.drawString(400, y_position, "Time")
    
    y_position -= 5
    c.line(50, y_position, width - 50, y_position)
    y_position -= 20
    
    c.setFont("Helvetica", 10)
    
    for exam in exams:
        if y_position < 100:
            c.showPage()
            y_position = height - 50
            c.setFont("Helvetica", 10)
        
        c.drawString(50, y_position, exam.date.strftime("%b %d, %Y"))
        c.drawString(150, y_position, exam.date.strftime("%A"))
        c.drawString(220, y_position, f"{exam.subject.code} - {exam.subject.name}")
        c.drawString(400, y_position, f"{exam.start_time.strftime('%I:%M %p')} - {exam.end_time.strftime('%I:%M %p')}")
        
        y_position -= 25
    
    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width/2, 50, "Important: Arrive 15 minutes before exam time. Bring your student ID card.")
    c.drawCentredString(width/2, 35, "Mobile phones and electronic devices are strictly prohibited.")
    
    c.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="timetable_{student.roll_number}.pdf"'
    
    return response