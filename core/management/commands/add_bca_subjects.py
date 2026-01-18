from django.core.management.base import BaseCommand
from core.models import Subject

class Command(BaseCommand):
    help = 'Add all BCA subjects to the database'

    def handle(self, *args, **kwargs):
        subjects = [
            # 1st Semester
            ('BCA101', 'Computer Fundamentals and Applications', 1),
            ('BCA102', 'Programming in C', 1),
            ('BCA103', 'Digital Logic', 1),
            ('BCA104', 'Mathematics I', 1),
            ('BCA105', 'Professional Communication and Ethics', 1),
            ('BCA106', 'Hardware Workshop', 1),
            
            # 2nd Semester
            ('BCA151', 'Discrete Structure', 2),
            ('BCA152', 'Microprocessor and Computer Architecture', 2),
            ('BCA153', 'OOP in Java', 2),
            ('BCA154', 'Mathematics-II', 2),
            ('BCA155', 'UX/UI Design', 2),
            ('BCA156', 'Principles of Management', 2),
            
            # 3rd Semester
            ('BCA201', 'Data Structure and Algorithms', 3),
            ('BCA202', 'Database Management System', 3),
            ('BCA203', 'Web Technology-I', 3),
            ('BCA204', 'System Analysis and Design', 3),
            ('BCA205', 'Probability and Statistics', 3),
            ('BCA206', 'Applied Economics', 3),
            
            # 4th Semester
            ('BCA251', 'Operating Systems', 4),
            ('BCA252', 'Software Engineering', 4),
            ('BCA253', 'Numerical Methods', 4),
            ('BCA254', 'Python Programming', 4),
            ('BCA255', 'Web Technology-II', 4),
            ('BCA256', 'Project-I', 4),
            
            # 5th Semester
            ('BCA301', 'Computer Network', 5),
            ('BCA302', 'Artificial Intelligence', 5),
            ('BCA303', 'Advance Java Programming', 5),
            ('BCA304', 'MIS and e-Business', 5),
            ('BCA305', 'Society and Technology', 5),
            ('BCA306', 'Project-II', 5),
            
            # 6th Semester
            ('BCA351', 'Computer Graphics and animation', 6),
            ('BCA352', 'Mobile Programming', 6),
            ('BCA353', 'Cryptography and Network Security', 6),
            ('BCA354', 'Technical Writing', 6),
            ('BCA355', 'Distributed System', 6),
            ('BCA356', 'Project-III', 6),
            
            # 7th Semester
            ('BCA401', 'Cyber Security and Ethical Hacking', 7),
            ('BCA402', 'Software Project Management', 7),
            ('BCA403', 'Financial Accounting', 7),
            ('BCA404', 'Project-IV', 7),
            ('BCA405', 'Elective-I', 7),
            ('BCA406', 'Elective-II', 7),
            
            # 8th Semester
            ('BCA451', 'Cloud Computing', 8),
            ('BCA452', 'Internship', 8),
            ('BCA453', 'Elective-III', 8),
            ('BCA454', 'Elective-IV', 8),
        ]
        
        created_count = 0
        for code, name, semester in subjects:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'semester': semester,
                    'branch': 'BCA'
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {code} - {name}'))
            else:
                self.stdout.write(f'Already exists: {code} - {name}')
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal BCA subjects created: {created_count}'))