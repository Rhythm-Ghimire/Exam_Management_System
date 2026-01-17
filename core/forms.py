from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Student, Subject, ExamHall, Invigilator, Exam, Result


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    roll_number = forms.CharField(max_length=20, required=True)
    branch = forms.CharField(max_length=100, required=True)
    semester = forms.IntegerField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            Student.objects.create(
                user=user,
                roll_number=self.cleaned_data['roll_number'],
                branch=self.cleaned_data['branch'],
                semester=self.cleaned_data['semester']
            )
        
        return user


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['roll_number', 'branch', 'semester', 'fees_paid', 'attendance']


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['code', 'name', 'semester']


class ExamHallForm(forms.ModelForm):
    class Meta:
        model = ExamHall
        fields = ['name', 'capacity', 'is_available']


class InvigilatorForm(forms.ModelForm):
    class Meta:
        model = Invigilator
        fields = ['name', 'email', 'phone']


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['subject', 'date', 'start_time', 'end_time', 'semester']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['student', 'subject', 'exam', 'marks_obtained', 'max_marks']