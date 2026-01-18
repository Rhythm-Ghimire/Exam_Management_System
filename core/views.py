from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import JsonResponse, HttpResponse
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
        user_type = request.POST.get('user_type')
        
        if not user_type:
            messages.error(request, 'Please select whether you are Admin or Student')
            return render(request, 'login.html')
        
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user type matches
            if user_type == 'admin':
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    messages.success(request, f'Welcome Admin {user.get_full_name() or user.username}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'You are not authorized to login as Admin')
            elif user_type == 'student':
                if not user.is_staff:
                    # Check if student profile exists
                    try:
                        student = Student.objects.get(user=user)
                        login(request, user)
                        messages.success(request, f'Welcome {user.get_full_name() or user.username}!')
                        return redirect('dashboard')
                    except Student.DoesNotExist:
                        messages.error(request, 'Student profile not found. Please contact admin.')
                else:
                    messages.error(request, 'Admin accounts cannot login as Student')
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
            student = Student.objects.get(user=request.user)
            seating = SeatingArrangement.objects.filter(student=student).select_related('exam', 'hall', 'exam__schedule')
            results = Result.objects.filter(student=student).select_related('subject', 'exam')
            
            # Get upcoming exams for student's semester and branch
            upcoming_exams = Exam.objects.filter(
                schedule__semester=student.semester,
                schedule__branch=student.branch
            ).select_related('schedule', 'subject').order_by('date')[:5]
            
            context = {
                'student': student,
                'seating_arrangements': seating,
                'results': results,
                'upcoming_exams': upcoming_exams
            }
            return render(request, 'student_dashboard.html', context)
        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found. Please contact admin.')
            return redirect('index')


@login_required
@user_passes_test(is_admin)
def students_overview(request):
    """Show all students grouped by branch and semester"""
    students = Student.objects.all().select_related('user').order_by('branch', 'semester', 'roll_number')
    
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
    
    # Get subjects and exams for each semester
    subjects_by_semester = {}
    exams_by_semester = {}
    
    for semester in range(1, 9):
        subjects_by_semester[semester] = Subject.objects.filter(semester=semester)
        exams_by_semester[semester] = Exam.objects.filter(semester=semester)
    
    context = {
        'grouped_students': grouped_students,
        'subjects_by_semester': subjects_by_semester,
        'exams_by_semester': exams_by_semester,
        'total_students': students.count(),
        'paid_fees': students.filter(fees_paid=True).count(),
        'unpaid_fees': students.filter(fees_paid=False).count(),
    }
    
    return render(request, 'students_overview.html', context)


@login_required
@user_passes_test(is_admin)
def manage_students(request):
    students = Student.objects.all().select_related('user')
    return render(request, 'manage_students.html', {'students': students})


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
    # Get subjects grouped by branch and semester
    bsccsit_subjects = {}
    bca_subjects = {}
    
    for sem in range(1, 9):
        bsccsit_subjects[sem] = Subject.objects.filter(branch='BScCSIT', semester=sem).order_by('code')
        bca_subjects[sem] = Subject.objects.filter(branch='BCA', semester=sem).order_by('code')
    
    context = {
        'bsccsit_subjects': bsccsit_subjects,
        'bca_subjects': bca_subjects,
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
    schedules = ExamSchedule.objects.all().prefetch_related('exams__subject').order_by('-created_at')
    
    # Debug: print to console
    print(f"Found {schedules.count()} schedules")
    for schedule in schedules:
        print(f"Schedule: {schedule.name}, Exams: {schedule.exams.count()}")
    
    return render(request, 'manage_exams.html', {'schedules': schedules})


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
def add_exam(request):
    if request.method == 'POST':
        subject = Subject.objects.get(id=request.POST.get('subject'))
        branch = request.POST.get('branch')
        semester = int(request.POST.get('semester'))
        exam_type = request.POST.get('exam_type')
        
        # Create or get exam schedule
        schedule_name = f"{branch} Semester {semester} {exam_type.replace('_', ' ').title()} {request.POST.get('date')[:4]}"
        schedule, created = ExamSchedule.objects.get_or_create(
            branch=branch,
            semester=semester,
            exam_type=exam_type,
            defaults={
                'name': schedule_name,
                'start_date': request.POST.get('date'),
                'end_date': request.POST.get('date')
            }
        )
        
        # Create exam
        Exam.objects.create(
            schedule=schedule,
            subject=subject,
            date=request.POST.get('date'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time')
        )
        
        messages.success(request, f'Exam added successfully to {schedule_name}!')
        return redirect('manage_exams')
    
    subjects = Subject.objects.all()
    return render(request, 'add_exam.html', {'subjects': subjects})


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
    """Generate seating for all exams in a schedule"""
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    exams = schedule.exams.all()
    
    if not exams.exists():
        messages.error(request, 'No exams found in this schedule.')
        return redirect('manage_exams')
    
    # Get eligible students for this semester
    students = Student.objects.filter(
        semester=schedule.semester,
        branch=schedule.branch,
        fees_paid=True,
        attendance__gte=75.0
    ).order_by('roll_number')
    
    if not students.exists():
        messages.error(request, f'No eligible students found for {schedule.branch} Semester {schedule.semester}.')
        return redirect('manage_exams')
    
    # Get available halls
    halls = ExamHall.objects.filter(is_available=True).order_by('-capacity')
    
    if not halls.exists():
        messages.error(request, 'No available exam halls found.')
        return redirect('manage_exams')
    
    # Get invigilators
    invigilators = Invigilator.objects.all()
    
    success_count = 0
    for exam in exams:
        # Clear existing arrangements
        SeatingArrangement.objects.filter(exam=exam).delete()
        InvigilatorAssignment.objects.filter(exam=exam).delete()
        
        # Generate seating
        if generate_seating_arrangement(exam, students, halls):
            if invigilators.exists():
                assign_invigilators(exam, halls, invigilators)
            success_count += 1
    
    if success_count == exams.count():
        messages.success(request, f'Successfully generated seating arrangements for all {success_count} exams in {schedule.name}!')
    else:
        messages.warning(request, f'Generated seating for {success_count} out of {exams.count()} exams.')
    
    return redirect('manage_exams')


@login_required
def view_seating(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.user.is_staff:
        seating = SeatingArrangement.objects.filter(exam=exam).select_related('student', 'hall').order_by('hall', 'seat_number')
        invigilators = InvigilatorAssignment.objects.filter(exam=exam).select_related('invigilator', 'hall')
        
        # Group by hall
        halls_data = {}
        for seat in seating:
            if seat.hall.name not in halls_data:
                halls_data[seat.hall.name] = []
            halls_data[seat.hall.name].append(seat)
        
        context = {
            'exam': exam,
            'halls_data': halls_data,
            'invigilators': invigilators
        }
        return render(request, 'view_seating.html', context)
    else:
        try:
            student = Student.objects.get(user=request.user)
            seating = SeatingArrangement.objects.filter(exam=exam, student=student).first()
            
            context = {
                'exam': exam,
                'seating': seating
            }
            return render(request, 'student_seating.html', context)
        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found.')
            return redirect('dashboard')


@login_required
def download_seating_pdf(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    seating = SeatingArrangement.objects.filter(exam=exam).select_related('student', 'hall').order_by('hall', 'seat_number')
    invigilators = InvigilatorAssignment.objects.filter(exam=exam).select_related('invigilator', 'hall')
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph(f"<b>Seating Arrangement</b><br/>{exam.subject.name}<br/>{exam.date}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Group by hall
    halls_data = {}
    for seat in seating:
        if seat.hall.name not in halls_data:
            halls_data[seat.hall.name] = []
        halls_data[seat.hall.name].append(seat)
    
    # Create tables for each hall
    for hall_name, seats in halls_data.items():
        # Hall header
        hall_header = Paragraph(f"<b>{hall_name}</b>", styles['Heading2'])
        elements.append(hall_header)
        elements.append(Spacer(1, 10))
        
        # Find invigilator for this hall
        inv = invigilators.filter(hall__name=hall_name).first()
        if inv:
            inv_text = Paragraph(f"Invigilator: {inv.invigilator.name}", styles['Normal'])
            elements.append(inv_text)
            elements.append(Spacer(1, 10))
        
        # Seating table
        data = [['Seat No.', 'Roll Number', 'Name', 'Branch']]
        for seat in seats:
            data.append([
                seat.seat_number,
                seat.student.roll_number,
                seat.student.user.get_full_name(),
                seat.student.branch
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="seating_{exam.subject.code}_{exam.date}.pdf"'
    
    return response


@login_required
@user_passes_test(is_admin)
def results_home(request):
    """Step 1: Select Branch"""
    branches = [
        {'code': 'BScCSIT', 'name': 'BScCSIT - Bachelor of Science in Computer Science and Information Technology'},
        {'code': 'BCA', 'name': 'BCA - Bachelor of Computer Applications'}
    ]
    return render(request, 'results_home.html', {'branches': branches})


@login_required
@user_passes_test(is_admin)
def results_semester_list(request, branch):
    """Step 2: Select Semester"""
    semesters = range(1, 9)
    student_counts = {}
    
    for sem in semesters:
        student_counts[sem] = Student.objects.filter(branch=branch, semester=sem).count()
    
    context = {
        'branch': branch,
        'semesters': semesters,
        'student_counts': student_counts
    }
    return render(request, 'results_semester_list.html', context)


@login_required
@user_passes_test(is_admin)
def results_student_list(request, branch, semester):
    """Step 3: Select Student"""
    students = Student.objects.filter(
        branch=branch,
        semester=semester
    ).select_related('user').order_by('roll_number')
    
    # Get result completion status for each student
    subjects = Subject.objects.filter(branch=branch, semester=semester)
    subject_count = subjects.count()
    
    student_data = []
    for student in students:
        result_count = Result.objects.filter(
            student=student,
            subject__in=subjects
        ).count()
        
        student_data.append({
            'student': student,
            'results_entered': result_count,
            'total_subjects': subject_count,
            'is_complete': result_count == subject_count and subject_count > 0
        })
    
    context = {
        'branch': branch,
        'semester': semester,
        'student_data': student_data,
        'subjects': subjects
    }
    return render(request, 'results_student_list.html', context)


@login_required
@user_passes_test(is_admin)
def student_marksheet(request, branch, semester, student_id):
    """Step 4: View/Edit Student Marksheet"""
    student = get_object_or_404(Student, id=student_id, branch=branch, semester=semester)
    subjects = Subject.objects.filter(branch=branch, semester=semester).order_by('code')
    
    # Get existing results
    results = {}
    for subject in subjects:
        result = Result.objects.filter(student=student, subject=subject).first()
        results[subject.id] = result
    
    context = {
        'student': student,
        'subjects': subjects,
        'results': results,
        'branch': branch,
        'semester': semester
    }
    return render(request, 'student_marksheet.html', context)


@login_required
@user_passes_test(is_admin)
def add_student_results(request, branch, semester, student_id):
    """Add/Update results for all subjects of a student"""
    student = get_object_or_404(Student, id=student_id, branch=branch, semester=semester)
    subjects = Subject.objects.filter(branch=branch, semester=semester).order_by('code')
    
    if request.method == 'POST':
        updated_count = 0
        created_count = 0
        
        for subject in subjects:
            marks_key = f'marks_{subject.id}'
            marks = request.POST.get(marks_key)
            
            if marks and marks.strip():
                marks_value = float(marks)
                
                # Get or create result
                result, created = Result.objects.get_or_create(
                    student=student,
                    subject=subject,
                    defaults={
                        'marks_obtained': marks_value,
                        'max_marks': 100,
                        'exam': None  # Can be linked to exam if needed
                    }
                )
                
                if not created:
                    result.marks_obtained = marks_value
                    result.save()
                    updated_count += 1
                else:
                    created_count += 1
        
        messages.success(request, f'Results saved! Created: {created_count}, Updated: {updated_count}')
        return redirect('student_marksheet', branch=branch, semester=semester, student_id=student_id)
    
    # Get existing results
    existing_results = {}
    for subject in subjects:
        result = Result.objects.filter(student=student, subject=subject).first()
        if result:
            existing_results[subject.id] = result.marks_obtained
    
    context = {
        'student': student,
        'subjects': subjects,
        'existing_results': existing_results,
        'branch': branch,
        'semester': semester
    }
    return render(request, 'add_student_results.html', context)


@login_required
@user_passes_test(is_admin)
def manage_results(request):
    results = Result.objects.all().select_related('student', 'subject', 'exam')
    return render(request, 'manage_results.html', {'results': results})


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
        # Admin analytics
        subjects = Subject.objects.all()
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
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'pass_percentage': round((passed / total) * 100, 2),
                    'avg_marks': round(avg_marks, 2) if avg_marks else 0
                })
        
        context = {'analytics_data': analytics_data}
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