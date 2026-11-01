from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    daily_goal_minutes = models.PositiveIntegerField(
        default=120,
        validators=[MinValueValidator(15)],
        help_text="Target study time per day in minutes"
    )
    preferred_days = models.CharField(
        max_length=100,
        default="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        help_text="Comma-separated preferred study days"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Subject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=20, default="#4f46e5")  # Indigo default
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def progress_percentage(self):
        total = self.topics.count()
        if total == 0:
            return 0
        completed = self.topics.filter(is_completed=True).count()
        return int((completed / total) * 100)


class Topic(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=150)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    estimated_minutes = models.PositiveIntegerField(
        default=45,
        validators=[MinValueValidator(5)]
    )
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_completed', 'title']

    def __str__(self):
        return f"{self.subject.name} - {self.title}"


class Exam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exams')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=150)
    exam_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['exam_date']

    def __str__(self):
        return f"{self.title} ({self.exam_date})"

    @property
    def days_remaining(self):
        delta = self.exam_date - timezone.localdate()
        return delta.days


class StudyTask(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='tasks')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=200)
    due_date = models.DateField()
    planned_minutes = models.PositiveIntegerField(
        default=45,
        validators=[MinValueValidator(5)]
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='planned')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', '-priority']
        indexes = [
            models.Index(fields=['user', 'status', 'due_date']),
        ]

    def __str__(self):
        return self.title


class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    task = models.ForeignKey(StudyTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='sessions')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    started_at = models.DateField(default=timezone.localdate)
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at', '-created_at']

    def __str__(self):
        return f"{self.subject.name} - {self.duration_minutes} mins on {self.started_at}"


class StudyPlanBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plan_blocks')
    task = models.ForeignKey(StudyTask, on_delete=models.CASCADE, related_name='plan_blocks')
    plan_date = models.DateField(default=timezone.localdate)
    allocated_minutes = models.PositiveIntegerField(default=45)
    score = models.FloatField(default=0.0, help_text="Explainable priority score (0-100)")
    score_explanation = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['plan_date', 'order']

    def __str__(self):
        return f"{self.plan_date} [#{self.order}] {self.task.title}"

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quiz_attempts')
    topic_title = models.CharField(max_length=150)
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=3)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"{self.subject.name} ({self.topic_title}): {self.score}/{self.total_questions}"

    @property
    def percentage(self):
        if self.total_questions == 0:
            return 0
        return int((self.score / self.total_questions) * 100)

class Flashcard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='flashcards')
    topic_title = models.CharField(max_length=150)
    front_question = models.TextField()
    back_answer = models.TextField()
    is_mastered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_mastered', '-created_at']

    def __str__(self):
        return f"[{self.subject.name}] {self.front_question[:50]}"