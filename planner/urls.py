from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('settings/', views.settings_view, name='settings'),

    # Subjects & Topics
    path('subjects/', views.subject_list_view, name='subject_list'),
    path('subjects/<int:pk>/', views.subject_detail_view, name='subject_detail'),
    path('subjects/<int:pk>/edit/', views.subject_edit_view, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete_view, name='subject_delete'),
    path('topics/<int:pk>/toggle/', views.topic_toggle_view, name='topic_toggle'),
    path('topics/<int:pk>/edit/', views.topic_edit_view, name='topic_edit'),
    path('topics/<int:pk>/delete/', views.topic_delete_view, name='topic_delete'),

    # Exams
    path('exams/', views.exam_list_view, name='exam_list'),
    path('exams/<int:pk>/edit/', views.exam_edit_view, name='exam_edit'),
    path('exams/<int:pk>/delete/', views.exam_delete_view, name='exam_delete'),

    # Study Tasks
    path('tasks/', views.task_list_view, name='task_list'),
    path('tasks/<int:pk>/toggle/', views.task_toggle_status_view, name='task_toggle'),
    path('tasks/<int:pk>/edit/', views.task_edit_view, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete_view, name='task_delete'),

    # Study Planner & Sessions
    path('plan/', views.study_plan_view, name='study_plan'),
    path('sessions/log/', views.log_session_view, name='log_session'),

    # Progress & AI Assistant
    path('progress/', views.progress_view, name='progress'),
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant'),

    path('progress/export-csv/', views.export_progress_csv_view, name='export_progress_csv'),
    path('ai-assistant/log-quiz/', views.log_quiz_attempt_view, name='log_quiz_attempt'),

    # Stage 1: Friction Reducers (Rollover, Bulk Syllabus Import, AI-to-Tasks)
    path('tasks/rollover/', views.rollover_overdue_tasks_view, name='rollover_tasks'),
    path('subjects/<int:pk>/bulk-import/', views.bulk_import_topics_view, name='bulk_import_topics'),
    path('ai-assistant/convert-tasks/', views.convert_ai_to_tasks_view, name='convert_ai_to_tasks'),

    # Stage 2: 3D Flashcards Studio
    path('flashcards/', views.flashcard_list_view, name='flashcard_list'),
    path('flashcards/<int:pk>/toggle/', views.flashcard_toggle_mastered_view, name='flashcard_toggle'),
    path('flashcards/<int:pk>/delete/', views.flashcard_delete_view, name='flashcard_delete'),

    # Stage 3: Interactive Calendar & Adaptive Calibration
    path('calendar/', views.calendar_view, name='calendar_view'),
    path('subjects/<int:subject_pk>/calibrate/', views.apply_adaptive_estimate_view, name='apply_adaptive_estimate'),
]