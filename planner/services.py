from django.utils import timezone
from .models import Subject, StudyTask, StudyPlanBlock, StudySession
import os
import json
import urllib.request
import urllib.error
from django.conf import settings
import re
from django.db.models import Avg


def calculate_urgency_score(due_date):
    """Calculates urgency score from 0 to 100 based on days remaining until due date."""
    if not due_date:
        return 50.0
    today = timezone.localdate()
    days_left = (due_date - today).days
    
    if days_left <= 0:
        return 100.0  # Due today or overdue
    elif days_left == 1:
        return 90.0
    elif days_left <= 3:
        return 75.0
    elif days_left <= 7:
        return 50.0
    elif days_left <= 14:
        return 30.0
    else:
        return 10.0


def calculate_priority_score(priority_str):
    """Converts task priority choice to a 0-100 numeric score."""
    mapping = {'high': 100.0, 'medium': 60.0, 'low': 25.0}
    return mapping.get(priority_str, 50.0)


def calculate_difficulty_score(difficulty_str):
    """Converts topic difficulty choice to a 0-100 numeric score."""
    mapping = {'hard': 100.0, 'medium': 60.0, 'easy': 30.0}
    return mapping.get(difficulty_str, 50.0)


def generate_study_plan_for_user(user, target_date=None, available_minutes=120):
    """
    Explainable scheduling algorithm:
    Score = 0.50 * urgency + 0.30 * priority + 0.20 * difficulty
    Allocates incomplete tasks into the available minutes budget for the target date.
    """
    if target_date is None:
        target_date = timezone.localdate()

    # Clear existing plan blocks for this date so we can regenerate
    StudyPlanBlock.objects.filter(user=user, plan_date=target_date).delete()

    # Fetch pending tasks
    pending_tasks = StudyTask.objects.filter(
        user=user
    ).exclude(status='completed').select_related('subject', 'topic')

    scored_tasks = []
    for task in pending_tasks:
        urgency = calculate_urgency_score(task.due_date)
        priority = calculate_priority_score(task.priority)
        
        # Difficulty lookup from linked topic if available
        diff_str = task.topic.difficulty if task.topic else 'medium'
        difficulty = calculate_difficulty_score(diff_str)

        # Weighted composite score formula from Section 8.5
        score = (0.50 * urgency) + (0.30 * priority) + (0.20 * difficulty)
        explanation = f"Urgency: {int(urgency)} | Priority: {task.get_priority_display()} | Difficulty: {diff_str}"

        scored_tasks.append({
            'task': task,
            'score': round(score, 1),
            'explanation': explanation,
            'duration': task.planned_minutes
        })

    # Sort tasks highest score first, then earliest due date
    scored_tasks.sort(key=lambda x: (-x['score'], x['task'].due_date))

    allocated_blocks = []
    remaining_minutes = available_minutes
    order_index = 1

    for item in scored_tasks:
        task = item['task']
        duration = item['duration']

        # If task fits or we want to partially fit (here we check if time remains)
        if remaining_minutes >= duration:
            block = StudyPlanBlock.objects.create(
                user=user,
                task=task,
                plan_date=target_date,
                allocated_minutes=duration,
                score=item['score'],
                score_explanation=item['explanation'],
                order=order_index
            )
            allocated_blocks.append(block)
            remaining_minutes -= duration
            order_index += 1
        else:
            # If time budget is exhausted, we stop packing tasks for today
            break

    return allocated_blocks, remaining_minutes

def calculate_study_streak(user):
    """Calculates consecutive days the student has logged at least one study session."""
    session_dates = set(
        StudySession.objects.filter(user=user).values_list('started_at', flat=True)
    )
    if not session_dates:
        return 0

    today = timezone.localdate()
    streak = 0
    check_date = today if today in session_dates else (today - timezone.timedelta(days=1))

    while check_date in session_dates:
        streak += 1
        check_date -= timezone.timedelta(days=1)

    return streak


def generate_ai_study_assistance(topic_title, subject_name, difficulty, minutes, request_type="strategy", notes_text=""):
    """
    Calls Google Gemini API by automatically selecting an available model for the user's API key.
    Supports strategy, breakdown, quiz, explain, and summarize modes.
    """
    raw_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY", "")
    api_key = str(raw_key).strip().strip('"').strip("'")

    prompt_map = {
        "strategy": (
            f"You are an expert academic tutor. Create a detailed, personalized {minutes}-minute study plan "
            f"specifically for the topic '{topic_title}' in the subject '{subject_name}' (Difficulty: {difficulty}). "
            f"Include specific sub-concepts of '{topic_title}' to focus on, common pitfalls, and a minute-by-minute breakdown."
        ),
        "breakdown": (
            f"Break down the specific topic '{topic_title}' ({subject_name}, difficulty: {difficulty}) "
            f"into 4 concrete, topic-specific study sub-tasks that total {minutes} minutes. "
            f"Mention real concepts and sub-topics belonging to '{topic_title}'."
        ),
        "quiz": (
            f"Generate 3 actual multiple-choice questions (with options A, B, C, D) specifically testing "
            f"the topic '{topic_title}' in '{subject_name}' at a '{difficulty}' difficulty level. "
            f"At the end, provide the Answer Key with a brief explanation for each answer."
        ),
        "explain": (
            f"Explain the concept '{topic_title}' in the subject '{subject_name}' tailored for a '{difficulty}' level student. "
            f"Provide: 1) A simple intuition/analogy, 2) Core technical definition, and 3) One concrete example."
        ),
        "summarize": (
            f"Summarize the following student study notes on '{topic_title}' ({subject_name}) into crisp, high-yield exam revision bullet points "
            f"and highlight key terms to memorize:\n\n{notes_text or topic_title}"
        ),
    }
    prompt_text = prompt_map.get(request_type, prompt_map["strategy"])

    if api_key and api_key != "PASTE_YOUR_API_KEY_HERE":
        candidate_models = [
            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro",
            "models/gemini-pro",
        ]
        try:
            list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            with urllib.request.urlopen(list_url, timeout=10) as resp:
                models_data = json.loads(resp.read().decode("utf-8"))
                available = [
                    m["name"] for m in models_data.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                if available:
                    flash_models = [m for m in available if "flash" in m]
                    candidate_models = flash_models + [m for m in available if m not in flash_models]
        except Exception:
            pass

        last_error = None
        for model_name in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt_text}]}]
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=20) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    ai_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    clean_model = model_name.replace("models/", "")
                    return {
                        "source": f"Live Gemini AI ({clean_model})",
                        "content": ai_text,
                    }
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {http_err.code} on {model_name}: {err_body[:200]}"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        return {
            "source": "AI API Error",
            "content": f"Could not generate response with your API key.\nDetails: {last_error}",
        }

    return {
        "source": "Offline Mode",
        "content": f"Add GEMINI_API_KEY in config/settings.py for live AI generation on '{topic_title}'.",
    }

def generate_interactive_quiz_json(topic_title, subject_name, difficulty):
    """
    Generates 3 structured MCQ questions (JSON) for the interactive radio-button quiz grader.
    Uses Live Gemini API if configured, with a guaranteed structured fallback.
    """
    raw_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY", "")
    api_key = str(raw_key).strip().strip('"').strip("'")

    prompt = (
        f"Generate exactly 3 multiple-choice questions on the topic '{topic_title}' "
        f"in the subject '{subject_name}' (Difficulty: {difficulty}). "
        f"Return ONLY a raw JSON array of 3 objects (no markdown backticks) with keys: "
        f"\"question\" (string), \"options\" (array of 4 strings), "
        f"\"correct_index\" (integer 0 to 3), and \"explanation\" (string)."
    )

    if api_key and api_key != "PASTE_YOUR_API_KEY_HERE":
        candidate_models = ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash"]
        for model_name in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    clean_json = re.sub(r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE).strip()
                    parsed = json.loads(clean_json)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return parsed
            except Exception:
                continue

    # Structured Fallback if offline
    return [
        {
            "question": f"Which of the following best describes the primary objective of {topic_title} in {subject_name}?",
            "options": [
                f"Optimizing structure, accuracy, and efficiency within {subject_name}",
                "Increasing redundant overhead without validation",
                "Bypassing standard syntax and architectural constraints",
                f"Ignoring boundary conditions in {topic_title}"
            ],
            "correct_index": 0,
            "explanation": f"{topic_title} focuses on systematic organization and correctness in {subject_name}."
        },
        {
            "question": f"When applying {topic_title} at a {difficulty} level, what is the most important factor to verify first?",
            "options": [
                "Visual styling of the output",
                "Base assumptions, prerequisites, and edge cases",
                "Hardware clock speed",
                "Unrelated external libraries"
            ],
            "correct_index": 1,
            "explanation": "Verifying base constraints and edge cases prevents logic flaws."
        },
        {
            "question": f"How should you validate your solution when working on {topic_title}?",
            "options": [
                "Skip testing if the first step looks right",
                "Only memorize the definition without practice",
                "Test against standard examples and boundary cases",
                "Remove all constraints from the problem"
            ],
            "correct_index": 2,
            "explanation": "Testing against concrete and boundary cases ensures complete mastery."
        }
    ]


def generate_ai_flashcards_data(topic_title, subject_name):
    """Generates 4 Q&A flashcards for a topic using Gemini API or a smart fallback."""
    raw_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY", "")
    api_key = str(raw_key).strip().strip('"').strip("'")

    prompt = (
        f"Create 4 study flashcards for the topic '{topic_title}' in '{subject_name}'. "
        f"Return ONLY a raw JSON array of 4 objects (no markdown backticks) with keys: "
        f"\"front\" (concise question or key term) and \"back\" (clear, 1-2 sentence answer/definition)."
    )

    if api_key and api_key != "PASTE_YOUR_API_KEY_HERE":
        for model_name in ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    clean_json = re.sub(r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE).strip()
                    parsed = json.loads(clean_json)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return parsed
            except Exception:
                continue

    return [
        {"front": f"Core Definition: {topic_title}", "back": f"Fundamental concept in {subject_name} used to structure and solve domain problems."},
        {"front": f"Key Advantage of {topic_title}", "back": "Improves reliability, clarity, and systematic problem-solving during exams."},
        {"front": f"Common Pitfall in {topic_title}", "back": "Overlooking base conditions or skipping step-by-step verification."},
        {"front": f"Exam Application of {topic_title}", "back": f"Frequently tested via worked examples and comparative questions in {subject_name}."}
    ]

def get_adaptive_time_recommendations(user):
    """
    Compares average actual StudySession duration vs average StudyTask planned_minutes
    per subject. Returns recommendations where actual effort exceeds planned time by >=20%.
    """
    recommendations = []
    subjects = Subject.objects.filter(user=user)

    for subject in subjects:
        avg_planned = StudyTask.objects.filter(
            user=user, subject=subject
        ).aggregate(avg=Avg('planned_minutes'))['avg']

        avg_actual = StudySession.objects.filter(
            user=user, subject=subject
        ).aggregate(avg=Avg('duration_minutes'))['avg']

        if avg_planned and avg_actual and avg_actual >= (avg_planned * 1.20):
            suggested_mins = int(round(avg_actual / 5.0) * 5)
            recommendations.append({
                'subject': subject,
                'avg_planned': int(avg_planned),
                'avg_actual': int(avg_actual),
                'suggested_minutes': max(15, suggested_mins),
            })

    return recommendations