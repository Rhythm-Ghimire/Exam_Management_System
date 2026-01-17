from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Student Management
    path('students/', views.manage_students, name='manage_students'),
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
    path('exams/add/', views.add_exam, name='add_exam'),
    path('exams/<int:exam_id>/generate-seating/', views.generate_seating, name='generate_seating'),
    path('exams/<int:exam_id>/seating/', views.view_seating, name='view_seating'),
    path('exams/<int:exam_id>/seating/download/', views.download_seating_pdf, name='download_seating_pdf'),
    
    # Results
    path('results/', views.manage_results, name='manage_results'),
    path('results/add/', views.add_result, name='add_result'),
    
    # Analytics
    path('analytics/', views.performance_analytics, name='performance_analytics'),
    
    # Timetable
    path('timetable/', views.timetable, name='timetable'),
]