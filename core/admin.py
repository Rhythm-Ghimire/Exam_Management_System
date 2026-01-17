from django.contrib import admin
from .models import Student, Subject, ExamHall, Invigilator, Exam, SeatingArrangement, InvigilatorAssignment, Result

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['roll_number', 'user', 'branch', 'semester', 'fees_paid', 'attendance', 'is_eligible']
    list_filter = ['branch', 'semester', 'fees_paid']
    search_fields = ['roll_number', 'user__username', 'user__first_name', 'user__last_name']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'semester']
    list_filter = ['semester']
    search_fields = ['code', 'name']

@admin.register(ExamHall)
class ExamHallAdmin(admin.ModelAdmin):
    list_display = ['name', 'capacity', 'is_available']
    list_filter = ['is_available']

@admin.register(Invigilator)
class InvigilatorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone']
    search_fields = ['name', 'email']

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['subject', 'date', 'start_time', 'end_time', 'semester']
    list_filter = ['date', 'semester']
    search_fields = ['subject__name', 'subject__code']

@admin.register(SeatingArrangement)
class SeatingArrangementAdmin(admin.ModelAdmin):
    list_display = ['exam', 'student', 'hall', 'seat_number']
    list_filter = ['exam', 'hall']
    search_fields = ['student__roll_number']

@admin.register(InvigilatorAssignment)
class InvigilatorAssignmentAdmin(admin.ModelAdmin):
    list_display = ['exam', 'invigilator', 'hall']
    list_filter = ['exam']

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'marks_obtained', 'max_marks', 'grade']
    list_filter = ['grade', 'subject']
    search_fields = ['student__roll_number']