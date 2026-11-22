from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==================== PUBLIC & AUTHENTICATION ====================
    path('', views.landing_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),

    # ==================== CORE DASHBOARD, PROFILE & SETTINGS ====================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),

    # ==================== SUBJECTS & TOPICS ====================
    path('subjects/', views.subject_list_view, name='subject_list'),
    path('subjects/<int:pk>/', views.subject_detail_view, name='subject_detail'),
    path('subjects/<int:pk>/edit/', views.edit_subject_view, name='edit_subject'),
    path('subjects/<int:pk>/delete/', views.delete_subject_view, name='delete_subject'),
    path('subjects/<int:pk>/bulk-import/', views.bulk_import_topics_view, name='bulk_import_topics'),
    path('subjects/<int:subject_pk>/calibrate/', views.apply_adaptive_estimate_view, name='apply_adaptive_estimate'),

    path('topics/<int:pk>/toggle/', views.topic_toggle_view, name='topic_toggle'),
    path('topics/<int:pk>/edit/', views.edit_topic_view, name='edit_topic'),
    path('topics/<int:pk>/delete/', views.delete_topic_view, name='delete_topic'),

    # ==================== EXAMS ====================
    path('exams/', views.exam_list_view, name='exam_list'),
    path('exams/<int:pk>/edit/', views.exam_edit_view, name='exam_edit'),
    path('exams/<int:pk>/delete/', views.exam_delete_view, name='exam_delete'),

    # ==================== STUDY TASKS ====================
    path('tasks/', views.task_list_view, name='task_list'),
    path('tasks/<int:pk>/toggle/', views.task_toggle_status_view, name='task_toggle'),
    path('tasks/<int:pk>/edit/', views.task_edit_view, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete_view, name='task_delete'),
    path('tasks/rollover/', views.rollover_overdue_tasks_view, name='rollover_tasks'),

    # ==================== STUDY PLANNER, CALENDAR & SESSIONS ====================
    path('plan/', views.study_plan_view, name='study_plan'),
    path('calendar/', views.calendar_view, name='calendar_view'),
    path('sessions/log/', views.log_session_view, name='log_session'),

    # ==================== 3D FLASHCARDS STUDIO ====================
    path('flashcards/', views.flashcard_list_view, name='flashcard_list'),
    path('flashcards/<int:pk>/toggle/', views.flashcard_toggle_mastered_view, name='flashcard_toggle'),
    path('flashcards/<int:pk>/delete/', views.flashcard_delete_view, name='flashcard_delete'),

    # ==================== PROGRESS, ANALYTICS & AI ASSISTANT ====================
    path('progress/', views.progress_view, name='progress'),
    path('progress/export-csv/', views.export_progress_csv_view, name='export_progress_csv'),
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant'),
    path('ai-assistant/log-quiz/', views.log_quiz_attempt_view, name='log_quiz_attempt'),
    path('ai-assistant/convert-tasks/', views.convert_ai_to_tasks_view, name='convert_ai_to_tasks'),
]