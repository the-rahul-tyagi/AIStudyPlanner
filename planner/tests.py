from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Subject, Topic, StudyTask, StudyPlanBlock
from .services import generate_study_plan_for_user


class StudyPlannerTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='student_a', password='password123')
        self.user_b = User.objects.create_user(username='student_b', password='password123')
        self.subject_a = Subject.objects.create(user=self.user_a, name='DBMS')
        self.topic_a = Topic.objects.create(
            subject=self.subject_a,
            title='Normalization',
            difficulty='hard',
            estimated_minutes=60
        )

    def test_dashboard_requires_authentication(self):
        """Test 1: Opening dashboard while logged out redirects to login."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_cross_user_ownership_protection(self):
        """Test 2: User B cannot view or delete User A's subject."""
        self.client.login(username='student_b', password='password123')
        response = self.client.get(reverse('subject_detail', args=[self.subject_a.pk]))
        self.assertEqual(response.status_code, 404)

    def test_subject_creation(self):
        """Test 3: Authenticated user can create a subject."""
        self.client.login(username='student_a', password='password123')
        response = self.client.post(reverse('subject_list'), {
            'name': 'Operating Systems',
            'description': 'Process scheduling and memory management',
            'color': '#4f46e5'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subject.objects.filter(user=self.user_a, name='Operating Systems').exists())

    def test_planner_respects_available_time_budget(self):
        """Test 4: Planner schedules highest-priority tasks within available time budget."""
        today = timezone.localdate()
        t1 = StudyTask.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=self.topic_a,
            title='High Priority Urgent Task',
            due_date=today,
            planned_minutes=50,
            priority='high'
        )
        t2 = StudyTask.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            title='Low Priority Long Task',
            due_date=today + timezone.timedelta(days=10),
            planned_minutes=60,
            priority='low'
        )

        # Available time is 60 mins -> only t1 (50 mins) fits; t2 (60 mins) exceeds remaining 10 mins
        blocks, remaining = generate_study_plan_for_user(self.user_a, target_date=today, available_minutes=60)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].task, t1)
        self.assertEqual(remaining, 10)