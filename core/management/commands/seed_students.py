from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Student, Subject, Exam, Result
import random


class Command(BaseCommand):
    help = 'Seed 20 students per semester for BScCSIT and BCA with random results'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting seed process...'))

        branches = ['BScCSIT', 'BCA']
        semesters = range(1, 9)  # 1 to 8

        total_students = 0
        total_results = 0

        for branch in branches:
            branch_code = 'CSC' if branch == 'BScCSIT' else 'BCA'

            for semester in semesters:
                self.stdout.write(f'\n📚 Creating {branch} Semester {semester} students...')

                # Get subjects for this branch and semester
                subjects = list(Subject.objects.filter(
                    branch=branch,
                    semester=semester
                ))

                if not subjects:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠️  No subjects found for {branch} Semester {semester}. Skipping results.'
                        )
                    )

                for i in range(1, 21):  # 20 students per semester
                    # Build unique identifiers
                    username = f'{branch_code.lower()}_s{semester}_student{i}'
                    roll_number = f'{branch_code}{semester}{str(i).zfill(3)}'

                    # Skip if already exists
                    if User.objects.filter(username=username).exists():
                        self.stdout.write(f'  ⏭️  Skipping {username} (already exists)')
                        continue

                    # Random fees and attendance
                    fees_paid = random.choice([True, True, False])  # ~67% paid
                    attendance = round(random.uniform(55.0, 100.0), 2)

                    # Create Django User
                    user = User.objects.create_user(
                        username=username,
                        password='student123',
                        first_name=f'Student{i}',
                        last_name=f'{branch}{semester}',
                        email=f'{username}@college.edu'
                    )

                    # Create Student profile
                    student = Student.objects.create(
                        user=user,
                        roll_number=roll_number,
                        branch=branch,
                        semester=semester,
                        fees_paid=fees_paid,
                        attendance=attendance
                    )

                    total_students += 1

                    # Add results for subjects if exams exist
                    if subjects:
                        for subject in subjects:
                            # Find an exam for this subject
                            exam = Exam.objects.filter(
                                subject=subject,
                                schedule__semester=semester,
                                schedule__branch=branch
                            ).first()

                            if exam:
                                # Check if result already exists
                                if not Result.objects.filter(student=student, exam=exam).exists():
                                    marks = round(random.uniform(25.0, 100.0), 2)

                                    Result.objects.create(
                                        student=student,
                                        subject=subject,
                                        exam=exam,
                                        marks_obtained=marks,
                                        max_marks=100
                                    )
                                    total_results += 1

                    status = '✅ Eligible' if student.is_eligible() else '❌ Not Eligible'
                    fees = '💰 Paid' if fees_paid else '🚫 Unpaid'
                    self.stdout.write(
                        f'  ✔️  Created: {roll_number} | {username} | '
                        f'Attendance: {attendance}% | {fees} | {status}'
                    )

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(
            f'✅ Seeding complete!\n'
            f'   👥 Students created : {total_students}\n'
            f'   📊 Results created  : {total_results}\n'
            f'   🔑 Password for all : student123'
        ))
        self.stdout.write('='*60)