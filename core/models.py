from django.db import models
from django.contrib.auth.models import User


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=20, unique=True)
    branch = models.CharField(max_length=100)
    semester = models.IntegerField()
    fees_paid = models.BooleanField(default=False)
    attendance = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name()}"
    
    def is_eligible(self):
        return self.fees_paid and self.attendance >= 75.0


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    semester = models.IntegerField()
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ExamHall(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} (Capacity: {self.capacity})"


class Invigilator(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    
    def __str__(self):
        return self.name


class Exam(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    semester = models.IntegerField()
    
    def __str__(self):
        return f"{self.subject.name} - {self.date}"
    
    class Meta:
        ordering = ['date', 'start_time']


class SeatingArrangement(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    hall = models.ForeignKey(ExamHall, on_delete=models.CASCADE)
    seat_number = models.IntegerField()
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.hall.name} - Seat {self.seat_number}"
    
    class Meta:
        unique_together = ['exam', 'student']


class InvigilatorAssignment(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    invigilator = models.ForeignKey(Invigilator, on_delete=models.CASCADE)
    hall = models.ForeignKey(ExamHall, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.invigilator.name} - {self.exam.subject.name} - {self.hall.name}"
    
    class Meta:
        unique_together = ['exam', 'hall']


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    marks_obtained = models.FloatField()
    max_marks = models.FloatField(default=100)
    grade = models.CharField(max_length=5, blank=True)
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.subject.code} - {self.marks_obtained}"
    
    def save(self, *args, **kwargs):
        percentage = (self.marks_obtained / self.max_marks) * 100
        if percentage >= 90:
            self.grade = 'A+'
        elif percentage >= 80:
            self.grade = 'A'
        elif percentage >= 70:
            self.grade = 'B+'
        elif percentage >= 60:
            self.grade = 'B'
        elif percentage >= 50:
            self.grade = 'C+'
        elif percentage >= 40:
            self.grade = 'C'
        else:
            self.grade = 'F'
        super().save(*args, **kwargs)
    
    class Meta:
        unique_together = ['student', 'exam']