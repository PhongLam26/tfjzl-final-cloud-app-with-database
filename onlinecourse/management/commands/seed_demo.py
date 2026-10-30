from datetime import date
from pathlib import Path
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import F

from onlinecourse.models import Choice, Course, Enrollment, Instructor, Learner, Lesson, Question


class Command(BaseCommand):
    help = 'Create or refresh a sample course, assessment, and local test accounts.'

    def handle(self, *args, **options):
        User = get_user_model()
        credentials_path = Path(settings.BASE_DIR) / '.local-credentials.txt'
        saved_credentials = self._read_credentials(credentials_path)

        admin_user = self._ensure_user(
            User, 'admin', saved_credentials, credentials_path,
            first_name='Course', last_name='Administrator', is_staff=True, is_superuser=True,
        )
        student = self._ensure_user(
            User, 'demo', saved_credentials, credentials_path,
            first_name='Alex', last_name='Learner', is_staff=False, is_superuser=False,
        )
        self._write_credentials(credentials_path, saved_credentials)

        instructor, _ = Instructor.objects.get_or_create(
            user=admin_user,
            defaults={'full_time': True, 'total_learners': 1},
        )
        course, _ = Course.objects.get_or_create(
            name='Python and Django Essentials',
            defaults={
                'image': 'course_images/python.png',
                'description': 'Build a strong foundation in Python, Django models, and secure web forms.',
                'pub_date': date.today(),
                'total_enrollment': 0,
            },
        )
        if not course.image:
            course.image = 'course_images/python.png'
            course.save(update_fields=['image'])
        course.instructors.add(instructor)

        lesson_specs = [
            (0, 'Python collections', 'Learn how Python stores and works with collections of values.'),
            (1, 'Django data models', 'Connect related records with Django model fields.'),
            (2, 'Secure web forms', 'Protect form submissions and validate input on the server.'),
        ]
        questions = [
            ('What does len([10, 20, 30]) return?', 2, [
                ('3', True), ('2', False), ('An error', False),
            ]),
            ('Which Django field creates a many-to-one relationship?', 1, [
                ('ForeignKey', True), ('ManyToManyField', False), ('OneToOneField', False),
            ]),
            ('What does a CSRF token help protect against?', 3, [
                ('Cross-site request forgery', True), ('Slow database queries', False), ('Weak passwords', False),
            ]),
        ]

        lessons_by_order = {}
        for order, title, content in lesson_specs:
            lesson, _ = Lesson.objects.update_or_create(
                course=course,
                order=order,
                defaults={'title': title, 'content': content},
            )
            lessons_by_order[order] = lesson

        for question_text, grade, choice_specs in questions:
            question, _ = Question.objects.update_or_create(
                course=course,
                question_text=question_text,
                defaults={'grade': grade},
            )
            for choice_text, is_correct in choice_specs:
                Choice.objects.update_or_create(
                    question=question,
                    choice_text=choice_text,
                    defaults={'is_correct': is_correct},
                )

        Learner.objects.get_or_create(
            user=student,
            defaults={
                'occupation': Learner.STUDENT,
                'social_link': 'https://example.org/demo-learner',
            },
        )
        _, enrollment_created = Enrollment.objects.get_or_create(
            user=student,
            course=course,
            defaults={'mode': Enrollment.HONOR},
        )
        if enrollment_created:
            Course.objects.filter(pk=course.pk).update(total_enrollment=F('total_enrollment') + 1)

        self.stdout.write(self.style.SUCCESS(
            f'Demo course ready (id={course.pk}); local credentials are in {credentials_path.name}.'
        ))

    @staticmethod
    def _read_credentials(path):
        if not path.exists():
            return {}
        credentials = {}
        for line in path.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                username, password = line.split('=', 1)
                credentials[username.strip()] = password.strip()
        return credentials

    @staticmethod
    def _ensure_user(User, username, credentials, credentials_path, **attributes):
        user, created = User.objects.get_or_create(username=username)
        password = credentials.get(username)
        if created or not password:
            password = password or secrets.token_urlsafe(24)
            user.set_password(password)
            credentials[username] = password
        for field, value in attributes.items():
            setattr(user, field, value)
        user.is_active = True
        user.save()
        return user

    @staticmethod
    def _write_credentials(path, credentials):
        lines = [
            '# Local demo accounts only. This ignored file must never be committed.',
            *(f'{username}={password}' for username, password in sorted(credentials.items())),
        ]
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
