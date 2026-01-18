from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Student Management
    path('students/', views.manage_students, name='manage_students'),
    path('students/overview/', views.students_overview, name='students_overview'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    
    # Subject Management
    path('subjects/', views.manage_subjects, name='manage_subjects'),
    path('subjects/add/', views.add_subject, name='add_subject'),
    
    # Hall Management
    path('halls/', views.manage_halls, name='manage_halls'),
    path('halls/add/', views.add_hall, name='add_hall'),
    
    # Invigilator Management
    path('invigilators/', views.manage_invigilators, name='manage_invigilators'),
    path('invigilators/add/', views.add_invigilator, name='add_invigilator'),
    
    # Exam Management
    path('exams/', views.manage_exams, name='manage_exams'),
    path('exams/create-schedule/', views.create_exam_schedule, name='create_exam_schedule'),
    path('exams/schedule/<int:schedule_id>/add-exam/', views.add_exam_to_schedule, name='add_exam_to_schedule'),
    path('exams/<int:exam_id>/generate-seating/', views.generate_seating, name='generate_seating'),
    path('exams/schedule/<int:schedule_id>/generate-seating/', views.generate_schedule_seating, name='generate_schedule_seating'),
    path('exams/<int:exam_id>/seating/', views.view_seating, name='view_seating'),
    path('exams/<int:exam_id>/seating/download/', views.download_seating_pdf, name='download_seating_pdf'),
    
    # Results
    path('results/', views.results_home, name='results_home'),
    path('results/<str:branch>/', views.results_semester_list, name='results_semester_list'),
    path('results/<str:branch>/<int:semester>/', views.results_student_list, name='results_student_list'),
    path('results/<str:branch>/<int:semester>/<int:student_id>/', views.student_marksheet, name='student_marksheet'),
    path('results/<str:branch>/<int:semester>/<int:student_id>/add/', views.add_student_results, name='add_student_results'),
    
    # Analytics
    path('analytics/', views.performance_analytics, name='performance_analytics'),
    
    # Timetable
    path('timetable/', views.timetable, name='timetable'),
    
    # API
    path('api/subjects/', views.get_subjects_api, name='get_subjects_api'),
]