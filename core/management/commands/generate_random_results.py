from django.core.management.base import BaseCommand
from core.models import Student, Exam, Result
import random


class Command(BaseCommand):
    help = 'Generate random results for all students in their own schedule exams only'

    def handle(self, *args, **kwargs):
        exams = Exam.objects.select_related('schedule', 'subject').all()
        total_results = 0

        if not exams.exists():
            self.stdout.write(self.style.ERROR('No exams found. Create exams first.'))
            return

        for exam in exams:
            if not exam.schedule:
                continue

            # ONLY get students from THIS exam's own branch + semester
            # Do NOT use SeatingArrangement to find students — it includes
            # cross-referenced students from other semesters sharing the same date
            students = Student.objects.filter(
                branch=exam.schedule.branch,
                semester=exam.schedule.semester,
                fees_paid=True,
                attendance__gte=75.0
            )

            subject = exam.subject

            for student in students:
                # Skip if result already exists
                if Result.objects.filter(student=student, subject=subject, exam=exam).exists():
                    continue

                # Generate random marks (70% chance pass, 30% fail)
                rand = random.random()
                if rand < 0.7:
                    marks = round(random.uniform(40, 100), 2)
                else:
                    marks = round(random.uniform(15, 39), 2)

                Result.objects.create(
                    student=student,
                    subject=subject,
                    exam=exam,
                    marks_obtained=marks,
                    max_marks=100
                )
                total_results += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Successfully created {total_results} results!'
        ))