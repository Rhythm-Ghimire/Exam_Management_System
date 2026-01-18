from django.core.management.base import BaseCommand
from core.models import Subject

class Command(BaseCommand):
    help = 'Add all BScCSIT subjects to the database'

    def handle(self, *args, **kwargs):
        subjects = [
            # Semester I
            ('CSC109', 'Introduction to Information Technology', 1),
            ('CSC110', 'C Programming', 1),
            ('CSC111', 'Digital Logic', 1),
            ('MTH112', 'Mathematics I', 1),
            ('PHY113', 'Physics', 1),
            
            # Semester II
            ('CSC160', 'Discrete Structure', 2),
            ('CSC161', 'Object Oriented Programming', 2),
            ('CSC162', 'Microprocessor', 2),
            ('MTH163', 'Mathematics II', 2),
            ('STA164', 'Statistics I', 2),
            
            # Semester III
            ('CSC206', 'Data Structure and Algorithms', 3),
            ('CSC207', 'Numerical Method', 3),
            ('CSC208', 'Computer Architecture', 3),
            ('CSC209', 'Computer Graphics', 3),
            ('STA210', 'Statistics II', 3),
            
            # Semester IV
            ('CSC257', 'Theory of Computation', 4),
            ('CSC258', 'Computer Networks', 4),
            ('CSC259', 'Operating Systems', 4),
            ('CSC260', 'Database Management System', 4),
            ('CSC261', 'Artificial Intelligence', 4),
            
            # Semester V
            ('CSC314', 'Design and Analysis of Algorithms', 5),
            ('CSC315', 'System Analysis and Design', 5),
            ('CSC316', 'Cryptography', 5),
            ('CSC317', 'Simulation and Modeling', 5),
            ('CSC318', 'Web Technology', 5),
            # Electives for Semester V
            ('CSC319', 'Multimedia Computing (Elective)', 5),
            ('CSC320', 'Wireless Networking (Elective)', 5),
            ('CSC321', 'Image Processing (Elective)', 5),
            ('CSC322', 'Knowledge Management (Elective)', 5),
            ('CSC323', 'Society and Ethics in Information Technology (Elective)', 5),
            ('CSC324', 'Microprocessor Based Design (Elective)', 5),
            
            # Semester VI
            ('CSC364', 'Software Engineering', 6),
            ('CSC365', 'Complier Design and Construction', 6),
            ('CSC366', 'E-Governance', 6),
            ('CSC367', 'NET Centric Computing', 6),
            ('CSC368', 'Technical Writing', 6),
            # Electives for Semester VI
            ('CSC369', 'Applied Logic (Elective)', 6),
            ('CSC370', 'E-commerce (Elective)', 6),
            ('CSC371', 'Automation and Robotics (Elective)', 6),
            ('CSC372', 'Neural Networks (Elective)', 6),
            ('CSC373', 'Computer Hardware Design (Elective)', 6),
            ('CSC374', 'Cognitive Science (Elective)', 6),
            
            # Semester VII
            ('CSC409', 'Advanced Java Programming', 7),
            ('CSC410', 'Data Warehousing and Data Mining', 7),
            ('MGT411', 'Principles of Management', 7),
            ('CSC412', 'Project Work', 7),
            # Electives for Semester VII
            ('CSC413', 'Information Retrieval (Elective)', 7),
            ('CSC414', 'Database Administration (Elective)', 7),
            ('CSC415', 'Software Project Management (Elective)', 7),
            ('CSC416', 'Network Security (Elective)', 7),
            ('CSC417', 'Digital System Design (Elective)', 7),
            ('MGT418', 'International Marketing (Elective)', 7),
            
            # Semester VIII
            ('CSC461', 'Advanced Database', 8),
            ('CSC462', 'Internship', 8),
            # Electives for Semester VIII
            ('CSC463', 'Advanced Networking with IPV6 (Elective)', 8),
            ('CSC464', 'Distributed Networking (Elective)', 8),
            ('CSC465', 'Game Technology (Elective)', 8),
            ('CSC466', 'Distributed and Object Oriented Database (Elective)', 8),
            ('CSC467', 'Introduction to Cloud Computing (Elective)', 8),
            ('CSC468', 'Geographical Information System (Elective)', 8),
            ('CSC469', 'Decision Support System and Expert System (Elective)', 8),
            ('CSC470', 'Mobile Application Development (Elective)', 8),
            ('CSC471', 'Real Time Systems (Elective)', 8),
            ('CSC472', 'Network and System Administration (Elective)', 8),
            ('CSC473', 'Embedded Systems Programming (Elective)', 8),
            ('MGT474', 'International Business Management (Elective)', 8),
        ]
        
        created_count = 0
        for code, name, semester in subjects:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'semester': semester,
                    'branch': 'BScCSIT'
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {code} - {name}'))
            else:
                self.stdout.write(f'Already exists: {code} - {name}')
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal subjects created: {created_count}'))