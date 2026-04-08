from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.index, name='index'),
    path('login/', views.user_login, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Students
    path('students/', views.manage_students, name='manage_students'),
    path('students/overview/', views.students_overview, name='students_overview'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),

    # Subjects
    path('subjects/', views.manage_subjects, name='manage_subjects'),
    path('subjects/add/', views.add_subject, name='add_subject'),

    # Halls
    path('halls/', views.manage_halls, name='manage_halls'),
    path('halls/add/', views.add_hall, name='add_hall'),
    path('halls/edit/<int:hall_id>/', views.edit_hall, name='edit_hall'),
    path('halls/delete/<int:hall_id>/', views.delete_hall, name='delete_hall'),

    # Invigilators
    path('invigilators/', views.manage_invigilators, name='manage_invigilators'),
    path('invigilators/add/', views.add_invigilator, name='add_invigilator'),
    path('invigilators/edit/<int:invigilator_id>/', views.edit_invigilator, name='edit_invigilator'),
    path('invigilators/delete/<int:invigilator_id>/', views.delete_invigilator, name='delete_invigilator'),

    # Exams & Schedules
    path('exams/', views.manage_exams, name='manage_exams'),
    path('exams/schedule/create/', views.create_exam_schedule, name='create_exam_schedule'),
    path('exams/schedule/<int:schedule_id>/add/', views.add_exam_to_schedule, name='add_exam_to_schedule'),
    path('exams/schedule/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),
    path('exams/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),

    # Seating
    path('exams/<int:exam_id>/seating/generate/', views.generate_seating, name='generate_seating'),
    path('exams/schedule/<int:schedule_id>/seating/generate/', views.generate_schedule_seating, name='generate_schedule_seating'),

    # NEW: smart seating generator per exam type (mid_term / final_term)
    path('exams/seating/generate/<str:exam_type>/', views.generate_seating_by_examtype, name='generate_seating_by_examtype'),

    path('exams/<int:exam_id>/seating/', views.view_seating, name='view_seating'),
    path('exams/<int:exam_id>/seating/pdf/', views.download_seating_pdf, name='download_seating_pdf'),

    # Results
    path('results/', views.manage_results, name='manage_results'),
    path('results/add/', views.add_result, name='add_result'),
    path('results/edit/<int:result_id>/', views.edit_result, name='edit_result'),
    path('results/delete/<int:result_id>/', views.delete_result, name='delete_result'),
    path('results/schedule/<int:schedule_id>/', views.schedule_results, name='schedule_results'),

    # Analytics & Timetable
    path('analytics/', views.performance_analytics, name='performance_analytics'),
    path('timetable/', views.timetable, name='timetable'),
    path('student/<int:student_id>/timetable/pdf/', views.download_student_timetable, name='download_student_timetable'),

    # API
    path('api/subjects/', views.get_subjects_api, name='get_subjects_api'),
]