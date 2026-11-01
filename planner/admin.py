from django.contrib import admin
from .models import (
    StudentProfile, Subject, Topic, Exam,
    StudyTask, StudySession, StudyPlanBlock, QuizAttempt, Flashcard
)

admin.site.register(StudentProfile)
admin.site.register(Subject)
admin.site.register(Topic)
admin.site.register(Exam)
admin.site.register(StudyTask)
admin.site.register(StudySession)
admin.site.register(StudyPlanBlock)
admin.site.register(QuizAttempt)
admin.site.register(Flashcard)