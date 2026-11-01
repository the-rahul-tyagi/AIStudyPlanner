import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from .forms import (
    StudentRegistrationForm, StudentProfileForm,
    SubjectForm, TopicForm, ExamForm, StudyTaskForm
)

import csv
from django.http import HttpResponse
from .models import (
    StudentProfile, Subject, Topic, Exam,
    StudyTask, StudySession, StudyPlanBlock, QuizAttempt, Flashcard
)
from .services import (
    generate_study_plan_for_user,
    generate_ai_study_assistance,
    calculate_study_streak,
    generate_interactive_quiz_json,
    generate_ai_flashcards_data,
    get_adaptive_time_recommendations,
)

import re


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'planner/landing.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            StudentProfile.objects.create(
                user=user,
                daily_goal_minutes=form.cleaned_data.get('daily_goal_minutes', 120)
            )
            login(request, user)
            messages.success(request, "Welcome! Your study planner account is ready.")
            return redirect('dashboard')
    else:
        form = StudentRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    start_of_week = today - timezone.timedelta(days=today.weekday())

    # 1. Summary Metrics
    tasks_due_today = StudyTask.objects.filter(
        user=request.user, due_date=today
    ).exclude(status='completed').count()

    pending_tasks = StudyTask.objects.filter(
        user=request.user
    ).exclude(status='completed').select_related('subject', 'topic')

    weekly_minutes = StudySession.objects.filter(
        user=request.user, started_at__gte=start_of_week
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0

    completed_topics_count = Topic.objects.filter(
        subject__user=request.user, is_completed=True
    ).count()
    total_topics_count = Topic.objects.filter(
        subject__user=request.user
    ).count()

    # 2. Upcoming Exams
    upcoming_exams = Exam.objects.filter(
        user=request.user, exam_date__gte=today
    ).select_related('subject').order_by('exam_date')[:4]

    # 3. Subjects with Topic Progress
    subjects = Subject.objects.filter(user=request.user).prefetch_related('topics')

    # 4. Last 7 Days Chart Data (Actual Study Minutes vs Daily Goal)
    chart_labels = []
    chart_actual_minutes = []
    chart_goal_minutes = []

    for i in range(6, -1, -1):
        day = today - timezone.timedelta(days=i)
        day_label = day.strftime('%a (%d %b)')
        day_total = StudySession.objects.filter(
            user=request.user, started_at=day
        ).aggregate(total=Sum('duration_minutes'))['total'] or 0

        chart_labels.append(day_label)
        chart_actual_minutes.append(day_total)
        chart_goal_minutes.append(profile.daily_goal_minutes)

    context = {
        'profile': profile,
        'tasks_due_today': tasks_due_today,
        'pending_tasks_count': pending_tasks.count(),
        'todays_tasks': pending_tasks.order_by('due_date', '-priority')[:6],
        'weekly_minutes': weekly_minutes,
        'completed_topics_count': completed_topics_count,
        'total_topics_count': total_topics_count,
        'upcoming_exams': upcoming_exams,
        'subjects': subjects,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_actual_json': json.dumps(chart_actual_minutes),
        'chart_goal_json': json.dumps(chart_goal_minutes),
    }
    # 5. Streak & 48-Hour Deadline Reminders
    streak_days = calculate_study_streak(request.user)
    two_days_later = today + timezone.timedelta(days=2)
    urgent_exams = Exam.objects.filter(user=request.user, exam_date__range=[today, two_days_later])
    urgent_tasks = StudyTask.objects.filter(
        user=request.user, due_date__range=[today, two_days_later]
    ).exclude(status='completed')

    return render(request, 'planner/dashboard.html', context)


@login_required
def settings_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your study preferences have been updated.")
            return redirect('settings')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'planner/settings.html', {'form': form})


# ==================== SUBJECTS & TOPICS CRUD ====================

@login_required
def subject_list_view(request):
    subjects = Subject.objects.filter(user=request.user).prefetch_related('topics')
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, f"Subject '{subject.name}' created.")
            return redirect('subject_list')
    else:
        form = SubjectForm()

    return render(request, 'planner/subject_list.html', {'subjects': subjects, 'form': form})


@login_required
def subject_detail_view(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    topics = subject.topics.all()

    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.subject = subject
            topic.save()
            messages.success(request, f"Topic '{topic.title}' added to {subject.name}.")
            return redirect('subject_detail', pk=subject.pk)
    else:
        form = TopicForm()

    return render(request, 'planner/subject_detail.html', {
        'subject': subject,
        'topics': topics,
        'form': form,
    })


@login_required
def subject_edit_view(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, "Subject updated successfully.")
            return redirect('subject_detail', pk=subject.pk)
    else:
        form = SubjectForm(instance=subject)

    return render(request, 'planner/form_page.html', {
        'title': f'Edit Subject: {subject.name}',
        'form': form,
        'cancel_url': 'subject_list',
    })


@login_required
def subject_delete_view(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    if request.method == 'POST':
        subject.delete()
        messages.info(request, "Subject deleted.")
        return redirect('subject_list')
    return render(request, 'planner/confirm_delete.html', {
        'object_name': subject.name,
        'cancel_url': 'subject_list',
    })


@login_required
def topic_toggle_view(request, pk):
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    if request.method == 'POST':
        topic.is_completed = not topic.is_completed
        topic.save()

        if topic.is_completed:
            # Auto-schedule Spaced Repetition revision tasks (+1d, +3d, +7d, +14d)
            today = timezone.localdate()
            intervals = [1, 3, 7, 14] if topic.difficulty == 'hard' else [3, 7]
            created_sr = 0
            for days in intervals:
                rev_title = f"[Spaced Revision +{days}d] {topic.title}"
                if not StudyTask.objects.filter(user=request.user, title=rev_title).exists():
                    StudyTask.objects.create(
                        user=request.user,
                        subject=topic.subject,
                        topic=topic,
                        title=rev_title,
                        due_date=today + timezone.timedelta(days=days),
                        planned_minutes=15,
                        priority='high' if topic.difficulty == 'hard' else 'medium',
                        status='planned'
                    )
                    created_sr += 1
            messages.success(
                request,
                f"Topic '{topic.title}' completed! Auto-scheduled {created_sr} Spaced-Repetition review tasks."
            )
        else:
            messages.info(request, f"Topic '{topic.title}' marked incomplete.")
    return redirect('subject_detail', pk=topic.subject.pk)


@login_required
def topic_edit_view(request, pk):
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    if request.method == 'POST':
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.success(request, "Topic updated.")
            return redirect('subject_detail', pk=topic.subject.pk)
    else:
        form = TopicForm(instance=topic)

    return render(request, 'planner/form_page.html', {
        'title': f'Edit Topic: {topic.title}',
        'form': form,
        'cancel_url': 'subject_list',
    })


@login_required
def topic_delete_view(request, pk):
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    subject_pk = topic.subject.pk
    if request.method == 'POST':
        topic.delete()
        messages.info(request, "Topic deleted.")
        return redirect('subject_detail', pk=subject_pk)
    return render(request, 'planner/confirm_delete.html', {
        'object_name': topic.title,
        'cancel_url': 'subject_list',
    })


# ==================== EXAMS CRUD ====================

@login_required
def exam_list_view(request):
    today = timezone.localdate()
    upcoming_exams = Exam.objects.filter(user=request.user, exam_date__gte=today).order_by('exam_date')
    past_exams = Exam.objects.filter(user=request.user, exam_date__lt=today).order_by('-exam_date')

    if request.method == 'POST':
        form = ExamForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.user = request.user
            exam.save()
            messages.success(request, f"Exam '{exam.title}' added.")
            return redirect('exam_list')
    else:
        form = ExamForm(user=request.user)

    return render(request, 'planner/exam_list.html', {
        'upcoming_exams': upcoming_exams,
        'past_exams': past_exams,
        'form': form,
    })


@login_required
def exam_edit_view(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Exam updated.")
            return redirect('exam_list')
    else:
        form = ExamForm(instance=exam, user=request.user)

    return render(request, 'planner/form_page.html', {
        'title': f'Edit Exam: {exam.title}',
        'form': form,
        'cancel_url': 'exam_list',
    })


@login_required
def exam_delete_view(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    if request.method == 'POST':
        exam.delete()
        messages.info(request, "Exam deleted.")
        return redirect('exam_list')
    return render(request, 'planner/confirm_delete.html', {
        'object_name': exam.title,
        'cancel_url': 'exam_list',
    })


# ==================== STUDY TASKS CRUD ====================

@login_required
def task_list_view(request):
    tasks = StudyTask.objects.filter(user=request.user).select_related('subject', 'topic')

    if request.method == 'POST':
        form = StudyTaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, f"Task '{task.title}' created.")
            return redirect('task_list')
    else:
        form = StudyTaskForm(user=request.user, initial={'due_date': timezone.localdate()})

    return render(request, 'planner/task_list.html', {'tasks': tasks, 'form': form})


@login_required
def task_toggle_status_view(request, pk):
    task = get_object_or_404(StudyTask, pk=pk, user=request.user)
    if request.method == 'POST':
        task.status = 'completed' if task.status != 'completed' else 'planned'
        task.save()
        if task.status == 'completed' and task.topic:
            task.topic.is_completed = True
            task.topic.save()
        messages.success(request, f"Task '{task.title}' marked as {task.get_status_display()}.")
    return redirect(request.META.get('HTTP_REFERER', 'task_list'))


@login_required
def task_edit_view(request, pk):
    task = get_object_or_404(StudyTask, pk=pk, user=request.user)
    if request.method == 'POST':
        form = StudyTaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Task updated.")
            return redirect('task_list')
    else:
        form = StudyTaskForm(instance=task, user=request.user)

    return render(request, 'planner/form_page.html', {
        'title': f'Edit Task: {task.title}',
        'form': form,
        'cancel_url': 'task_list',
    })


@login_required
def task_delete_view(request, pk):
    task = get_object_or_404(StudyTask, pk=pk, user=request.user)
    if request.method == 'POST':
        task.delete()
        messages.info(request, "Task deleted.")
        return redirect('task_list')
    return render(request, 'planner/confirm_delete.html', {
        'object_name': task.title,
        'cancel_url': 'task_list',
    })

# ==================== STUDY PLANNER & SESSIONS ====================

@login_required
def study_plan_view(request):
    today = timezone.localdate()
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    
    # Get user's generated plan blocks for today
    plan_blocks = StudyPlanBlock.objects.filter(
        user=request.user, plan_date=today
    ).select_related('task', 'task__subject', 'task__topic')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'generate':
            available_mins = int(request.POST.get('available_minutes', profile.daily_goal_minutes))
            generate_study_plan_for_user(request.user, target_date=today, available_minutes=available_mins)
            messages.success(request, f"Generated optimized study schedule for today ({available_mins} mins budget).")
            return redirect('study_plan')
        elif action == 'clear':
            plan_blocks.delete()
            messages.info(request, "Today's study plan has been cleared.")
            return redirect('study_plan')

    # Also grab past sessions for logging reference
    sessions = StudySession.objects.filter(user=request.user)[:10]

    context = {
        'plan_blocks': plan_blocks,
        'profile': profile,
        'today': today,
        'sessions': sessions,
    }
    return render(request, 'planner/study_plan.html', context)


@login_required
def log_session_view(request):
    if request.method == 'POST':
        subject_pk = request.POST.get('subject')
        task_pk = request.POST.get('task')
        duration = request.POST.get('duration_minutes')
        notes = request.POST.get('notes', '')

        subject = get_object_or_404(Subject, pk=subject_pk, user=request.user)
        task = StudyTask.objects.filter(pk=task_pk, user=request.user).first() if task_pk else None

        if duration and int(duration) > 0:
            StudySession.objects.create(
                user=request.user,
                subject=subject,
                task=task,
                topic=task.topic if task else None,
                duration_minutes=int(duration),
                notes=notes,
                started_at=timezone.localdate()
            )
            messages.success(request, f"Logged {duration} minutes of study for {subject.name}!")
        else:
            messages.error(request, "Please provide a valid study duration in minutes.")

    return redirect('study_plan')

# ==================== PROGRESS & ANALYTICS (PHASE 7) ====================

@login_required
def progress_view(request):
    today = timezone.localdate()
    days_range = int(request.GET.get('days', 7))
    if days_range not in [7, 14, 30]:
        days_range = 7

    start_date = today - timezone.timedelta(days=days_range - 1)

    sessions = StudySession.objects.filter(
        user=request.user, started_at__gte=start_date
    ).select_related('subject', 'task', 'topic')

    total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
    completed_tasks_count = StudyTask.objects.filter(
        user=request.user, status='completed'
    ).count()
    total_tasks_count = StudyTask.objects.filter(user=request.user).count()

    # Subject-wise study minutes breakdown for Doughnut chart
    subject_Usage = (
        sessions.values('subject__name', 'subject__color')
        .annotate(minutes=Sum('duration_minutes'))
        .order_by('-minutes')
    )
    subj_labels = [item['subject__name'] for item in subject_Usage]
    subj_minutes = [item['minutes'] for item in subject_Usage]
    subj_colors = [item['subject__color'] for item in subject_Usage]

    # Daily trend data over selected range
    trend_labels = []
    trend_minutes = []
    for i in range(days_range - 1, -1, -1):
        day = today - timezone.timedelta(days=i)
        day_sum = StudySession.objects.filter(
            user=request.user, started_at=day
        ).aggregate(total=Sum('duration_minutes'))['total'] or 0
        trend_labels.append(day.strftime('%d %b'))
        trend_minutes.append(day_sum)

    context = {
        'days_range': days_range,
        'sessions': sessions[:20],
        'total_minutes': total_minutes,
        'completed_tasks_count': completed_tasks_count,
        'total_tasks_count': total_tasks_count,
        'subj_labels_json': json.dumps(subj_labels),
        'subj_minutes_json': json.dumps(subj_minutes),
        'subj_colors_json': json.dumps(subj_colors),
        'trend_labels_json': json.dumps(trend_labels),
        'trend_minutes_json': json.dumps(trend_minutes),
    }
    return render(request, 'planner/progress.html', context)


# ==================== OPTIONAL AI ASSISTANT (PHASE 8) ====================

@login_required
def ai_assistant_view(request):
    subjects = Subject.objects.filter(user=request.user).prefetch_related('topics')
    quiz_attempts = QuizAttempt.objects.filter(user=request.user).select_related('subject')[:8]
    ai_response = None
    interactive_quiz_json = None
    selected_subject_pk = None
    tested_topic_title = ""

    if request.method == 'POST':
        subject_name = request.POST.get('subject_name', 'General Study').strip()
        topic_title = request.POST.get('topic_title', '').strip()
        difficulty = request.POST.get('difficulty', 'medium')
        minutes = int(request.POST.get('minutes', 45))
        request_type = request.POST.get('request_type', 'strategy')
        notes_text = request.POST.get('notes_text', '').strip()

        matched_subj = subjects.filter(name=subject_name).first() or subjects.first()
        selected_subject_pk = matched_subj.pk if matched_subj else None
        tested_topic_title = topic_title

        if topic_title:
            if request_type == 'quiz':
                quiz_list = generate_interactive_quiz_json(topic_title, subject_name, difficulty)
                interactive_quiz_json = json.dumps(quiz_list)
            ai_response = generate_ai_study_assistance(
                topic_title=topic_title,
                subject_name=subject_name,
                difficulty=difficulty,
                minutes=minutes,
                request_type=request_type,
                notes_text=notes_text,
            )
        else:
            messages.error(request, "Please enter a topic title to generate suggestions.")

    return render(request, 'planner/ai_assistant.html', {
        'subjects': subjects,
        'ai_response': ai_response,
        'interactive_quiz_json': interactive_quiz_json,
        'selected_subject_pk': selected_subject_pk,
        'tested_topic_title': tested_topic_title,
        'quiz_attempts': quiz_attempts,
    })


@login_required
def log_quiz_attempt_view(request):
    if request.method == 'POST':
        subject_pk = request.POST.get('subject')
        topic_title = request.POST.get('topic_title', '').strip()
        score = int(request.POST.get('score', 0))
        total_questions = int(request.POST.get('total_questions', 3))

        subject = get_object_or_404(Subject, pk=subject_pk, user=request.user)
        QuizAttempt.objects.create(
            user=request.user,
            subject=subject,
            topic_title=topic_title or "Practice Quiz",
            score=min(score, total_questions),
            total_questions=max(1, total_questions)
        )
        messages.success(request, f"Recorded quiz score {score}/{total_questions} for {subject.name}!")
    return redirect('ai_assistant')


@login_required
def export_progress_csv_view(request):
    """Exports the logged-in student's study sessions to a downloadable CSV report."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="study_progress_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Subject', 'Topic', 'Task', 'Duration (Minutes)', 'Notes'])

    sessions = StudySession.objects.filter(user=request.user).select_related('subject', 'topic', 'task')
    for s in sessions:
        writer.writerow([
            s.started_at,
            s.subject.name,
            s.topic.title if s.topic else '',
            s.task.title if s.task else '',
            s.duration_minutes,
            s.notes
        ])

    return response


# ==================== STAGE 1: FRICTION REDUCERS ====================

@login_required
def rollover_overdue_tasks_view(request):
    """Shifts all incomplete overdue tasks to today's date in one click."""
    if request.method == 'POST':
        today = timezone.localdate()
        overdue_tasks = StudyTask.objects.filter(
            user=request.user,
            due_date__lt=today
        ).exclude(status='completed')
        count = overdue_tasks.count()
        if count > 0:
            overdue_tasks.update(due_date=today)
            messages.success(request, f"Rolled over {count} overdue task(s) to today ({today})!")
        else:
            messages.info(request, "No overdue tasks found — you are right on schedule!")
    return redirect('dashboard')


@login_required
def bulk_import_topics_view(request, pk):
    """Parses pasted syllabus lines and bulk-creates Topic records for a Subject."""
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    if request.method == 'POST':
        raw_syllabus = request.POST.get('raw_syllabus', '').strip()
        default_difficulty = request.POST.get('default_difficulty', 'medium')
        default_minutes = int(request.POST.get('default_minutes', 45))

        lines = [line.strip() for line in raw_syllabus.splitlines() if line.strip()]
        created_count = 0
        for line in lines:
            # Clean leading bullet characters or numbers like "1. ", "- ", "• "
            clean_title = re.sub(r'^[\d\.\-\*\•\s]+', '', line).strip()
            if clean_title:
                Topic.objects.create(
                    subject=subject,
                    title=clean_title[:150],
                    difficulty=default_difficulty,
                    estimated_minutes=max(5, default_minutes)
                )
                created_count += 1

        if created_count > 0:
            messages.success(request, f"Bulk imported {created_count} topics into {subject.name}!")
        else:
            messages.warning(request, "Could not find any valid topic lines to import.")

    return redirect('subject_detail', pk=subject.pk)


@login_required
def convert_ai_to_tasks_view(request):
    """Extracts actionable lines from AI output and saves them as StudyTask records."""
    if request.method == 'POST':
        subject_name = request.POST.get('subject_name', '').strip()
        ai_content = request.POST.get('ai_content', '').strip()
        today = timezone.localdate()

        subject = Subject.objects.filter(user=request.user, name=subject_name).first()
        if not subject:
            subject = Subject.objects.filter(user=request.user).first()

        if not subject:
            messages.error(request, "Please create at least one Subject first before saving AI tasks.")
            return redirect('subject_list')

        # Match numbered items or bullet points from the AI response
        lines = [line.strip() for line in ai_content.splitlines() if line.strip()]
        task_lines = [
            re.sub(r'^[\d\.\-\*\•\#\s]+', '', line).strip()
            for line in lines
            if re.match(r'^(\d+[\.\)]|\-|\*|\•)\s+', line)
        ]

        # Fallback if AI didn't use standard bullets
        if not task_lines:
            task_lines = [line[:180] for line in lines if len(line) > 15][:4]

        created_count = 0
        for idx, title in enumerate(task_lines[:6]):
            clean_title = title.replace('**', '').strip()
            if clean_title:
                StudyTask.objects.create(
                    user=request.user,
                    subject=subject,
                    title=clean_title[:195],
                    due_date=today + timezone.timedelta(days=idx // 2),
                    planned_minutes=30,
                    priority='medium',
                    status='planned'
                )
                created_count += 1

        messages.success(request, f"Converted {created_count} AI steps into Study Tasks under {subject.name}!")
        return redirect('task_list')

    return redirect('ai_assistant')

# ==================== STAGE 2: 3D FLASHCARD STUDIO ====================

@login_required
def flashcard_list_view(request):
    subjects = Subject.objects.filter(user=request.user)
    flashcards = Flashcard.objects.filter(user=request.user).select_related('subject')

    if request.method == 'POST':
        action = request.POST.get('action', 'manual')
        subject_pk = request.POST.get('subject')
        topic_title = request.POST.get('topic_title', '').strip()
        subject = get_object_or_404(Subject, pk=subject_pk, user=request.user)

        if action == 'ai_generate' and topic_title:
            cards_data = generate_ai_flashcards_data(topic_title, subject.name)
            for item in cards_data:
                Flashcard.objects.create(
                    user=request.user,
                    subject=subject,
                    topic_title=topic_title,
                    front_question=item.get('front', topic_title),
                    back_answer=item.get('back', '')
                )
            messages.success(request, f"Generated {len(cards_data)} 3D Flashcards for '{topic_title}'!")
        else:
            front = request.POST.get('front_question', '').strip()
            back = request.POST.get('back_answer', '').strip()
            if front and back:
                Flashcard.objects.create(
                    user=request.user,
                    subject=subject,
                    topic_title=topic_title or "General",
                    front_question=front,
                    back_answer=back
                )
                messages.success(request, "Flashcard added to your deck!")

        return redirect('flashcard_list')

    return render(request, 'planner/flashcards.html', {
        'subjects': subjects,
        'flashcards': flashcards,
    })


@login_required
def flashcard_toggle_mastered_view(request, pk):
    card = get_object_or_404(Flashcard, pk=pk, user=request.user)
    if request.method == 'POST':
        card.is_mastered = not card.is_mastered
        card.save()
    return redirect('flashcard_list')


@login_required
def flashcard_delete_view(request, pk):
    card = get_object_or_404(Flashcard, pk=pk, user=request.user)
    if request.method == 'POST':
        card.delete()
        messages.info(request, "Flashcard removed.")
    return redirect('flashcard_list')

# ==================== STAGE 3: INTERACTIVE CALENDAR & ADAPTIVE AI ====================

@login_required
def calendar_view(request):
    """Renders an interactive FullCalendar view of all Exams, Tasks, and Plan Blocks."""
    exams = Exam.objects.filter(user=request.user).select_related('subject')
    tasks = StudyTask.objects.filter(user=request.user).select_related('subject')
    blocks = StudyPlanBlock.objects.filter(user=request.user).select_related('task', 'task__subject')
    recommendations = get_adaptive_time_recommendations(request.user)

    events = []
    for exam in exams:
        events.append({
            'title': f"🚨 EXAM: {exam.title} ({exam.subject.name})",
            'start': exam.exam_date.isoformat(),
            'color': '#ef4444',
            'url': '/exams/',
        })

    for task in tasks:
        prefix = "✅ " if task.status == 'completed' else "📌 "
        events.append({
            'title': f"{prefix}{task.title} ({task.planned_minutes}m)",
            'start': task.due_date.isoformat(),
            'color': '#10b981' if task.status == 'completed' else task.subject.color,
            'url': '/tasks/',
        })

    for block in blocks:
        events.append({
            'title': f"⚡ [Plan #{block.order}] {block.task.title}",
            'start': block.plan_date.isoformat(),
            'color': '#a855f7',
            'url': '/plan/',
        })

    return render(request, 'planner/calendar.html', {
        'events_json': json.dumps(events),
        'recommendations': recommendations,
    })


@login_required
def apply_adaptive_estimate_view(request, subject_pk):
    """Updates incomplete tasks and topics in a subject to the calibrated duration."""
    subject = get_object_or_404(Subject, pk=subject_pk, user=request.user)
    if request.method == 'POST':
        new_minutes = int(request.POST.get('suggested_minutes', 45))
        StudyTask.objects.filter(
            user=request.user, subject=subject
        ).exclude(status='completed').update(planned_minutes=new_minutes)
        Topic.objects.filter(
            subject=subject, is_completed=False
        ).update(estimated_minutes=new_minutes)
        messages.success(
            request,
            f"Calibrated pending tasks & topics in {subject.name} to {new_minutes} mins based on your study history!"
        )
    return redirect('calendar_view')