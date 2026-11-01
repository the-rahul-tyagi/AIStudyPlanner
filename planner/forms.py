from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import StudentProfile, Subject, Topic, Exam, StudyTask


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    daily_goal_minutes = forms.IntegerField(
        min_value=15,
        max_value=720,
        initial=120,
        help_text="Target daily study time in minutes (e.g., 120 for 2 hours)"
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['daily_goal_minutes', 'preferred_days']
        widgets = {
            'daily_goal_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 15}),
            'preferred_days': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Data Structures & Algorithms'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional course notes or syllabus summary'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['title', 'difficulty', 'estimated_minutes', 'is_completed', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Binary Search Trees'}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'estimated_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 5}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['subject', 'title', 'exam_date', 'notes']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Midterm Exam'}),
            'exam_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(user=user)


class StudyTaskForm(forms.ModelForm):
    class Meta:
        model = StudyTask
        fields = ['title', 'subject', 'topic', 'due_date', 'planned_minutes', 'priority', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Practice 10 Graph problems'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'planned_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 5}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(user=user)
            self.fields['topic'].queryset = Topic.objects.filter(subject__user=user)