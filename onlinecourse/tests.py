from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Choice, Course, Enrollment, Instructor, Learner, Lesson, Question, Submission


User = get_user_model()


class AssessmentTestData(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='test-password')
        self.other_user = User.objects.create_user(username='other', password='test-password')
        self.course = Course.objects.create(
            name='Django Basics',
            image='course_images/python.png',
            description='A short course used for assessment tests.',
        )
        self.lesson = Lesson.objects.create(
            title='Models', order=0, course=self.course, content='Django models describe data.'
        )
        self.second_lesson = Lesson.objects.create(
            title='Views', order=1, course=self.course, content='Views handle requests.'
        )
        self.question_one = Question.objects.create(
            lesson=self.lesson, question='Which is a Python list?', grade=2
        )
        self.correct_one = Choice.objects.create(
            question=self.question_one, choice='[1, 2, 3]', is_correct=True
        )
        self.wrong_one = Choice.objects.create(
            question=self.question_one, choice='{"a": 1}', is_correct=False
        )
        self.question_two = Question.objects.create(
            lesson=self.second_lesson, question='Which field links model rows many-to-one?', grade=3
        )
        self.correct_two = Choice.objects.create(
            question=self.question_two, choice='ForeignKey', is_correct=True
        )
        self.wrong_two = Choice.objects.create(
            question=self.question_two, choice='ManyToManyField', is_correct=False
        )
        self.enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, mode=Enrollment.HONOR
        )

    def log_in(self, user=None):
        self.client.force_login(user or self.user)


class AssessmentModelTests(AssessmentTestData):
    def test_course_lesson_question_choice_relationships(self):
        self.assertEqual(self.question_one.lesson, self.lesson)
        self.assertEqual(self.correct_one.question, self.question_one)
        self.assertEqual(list(self.course.lesson_set.order_by('order')), [self.lesson, self.second_lesson])
        self.assertEqual(self.lesson.question_set.count(), 1)
        self.assertEqual(self.question_one.choice_set.count(), 2)

    def test_submission_saves_and_retrieves_selected_choices(self):
        submission = Submission.objects.create(enrollment=self.enrollment)
        submission.choices.add(self.correct_one, self.correct_two)

        saved = Submission.objects.get(pk=submission.pk)
        self.assertEqual(saved.enrollment, self.enrollment)
        self.assertCountEqual(list(saved.choices.all()), [self.correct_one, self.correct_two])
        self.assertEqual(saved.choices.count(), 2)

    def test_question_score_method_requires_exact_correct_choices(self):
        self.assertTrue(self.question_one.is_get_score([self.correct_one.id]))
        self.assertFalse(self.question_one.is_get_score([self.wrong_one.id]))
        self.assertFalse(self.question_one.is_get_score([self.correct_one.id, self.wrong_one.id]))


class CoursePageTests(AssessmentTestData):
    def test_course_detail_shows_course_lesson_and_csrf_protected_exam_form(self):
        self.log_in()
        response = self.client.get(reverse('onlinecourse:course_details', args=(self.course.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Basics')
        self.assertContains(response, 'Models')
        self.assertContains(response, 'Which is a Python list?')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, reverse('onlinecourse:submit', args=(self.course.id,)))

    def test_course_list_is_available(self):
        response = self.client.get(reverse('onlinecourse:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.name)


class AssessmentViewTests(AssessmentTestData):
    def exam_url(self):
        return reverse('onlinecourse:submit', args=(self.course.id,))

    def result_url(self, submission_id):
        return reverse(
            'onlinecourse:show_exam_result', args=(self.course.id, submission_id)
        )

    def test_correct_answers_are_saved_and_receive_full_weighted_score(self):
        self.log_in()
        response = self.client.post(self.exam_url(), {
            f'choice_{self.question_one.id}': str(self.correct_one.id),
            f'choice_{self.question_two.id}': str(self.correct_two.id),
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        submission = Submission.objects.get(enrollment=self.enrollment)
        self.assertCountEqual(list(submission.choices.all()), [self.correct_one, self.correct_two])
        self.assertContains(response, 'Congratulations')
        self.assertContains(response, '5 / 5 points')
        self.assertEqual(response.context['selected_ids'], [self.correct_one.id, self.correct_two.id])
        self.assertEqual(response.context['possible'], 5)
        self.assertContains(response, '100.0%')
        self.assertContains(response, 'ForeignKey')

    def test_all_wrong_answers_fail(self):
        self.log_in()
        response = self.client.post(self.exam_url(), {
            f'choice_{self.question_one.id}': str(self.wrong_one.id),
            f'choice_{self.question_two.id}': str(self.wrong_two.id),
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assessment not passed')
        self.assertContains(response, '0 / 5 points')
        self.assertNotContains(response, 'Congratulations')

    def test_missing_answer_is_saved_as_unanswered_and_scores_zero_for_that_question(self):
        self.log_in()
        response = self.client.post(self.exam_url(), {
            f'choice_{self.question_one.id}': str(self.correct_one.id),
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        submission = Submission.objects.get(enrollment=self.enrollment)
        self.assertEqual(submission.choices.count(), 1)
        self.assertContains(response, '2 / 5 points')
        self.assertContains(response, 'Not answered')
        self.assertContains(response, '40.0%')

    def test_choice_from_another_question_is_rejected(self):
        self.log_in()
        response = self.client.post(self.exam_url(), {
            f'choice_{self.question_one.id}': str(self.correct_two.id),
            f'choice_{self.question_two.id}': str(self.correct_two.id),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_unknown_question_field_is_rejected(self):
        self.log_in()
        response = self.client.post(self.exam_url(), {
            f'choice_{self.question_one.id}': str(self.correct_one.id),
            'choice_999999': str(self.correct_two.id),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_submit_requires_login(self):
        response = self.client.post(self.exam_url(), {})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/onlinecourse/login/', response['Location'])

    def test_submit_requires_post(self):
        self.log_in()
        response = self.client.get(self.exam_url())
        self.assertEqual(response.status_code, 405)

    def test_submit_requires_enrollment(self):
        self.log_in(self.other_user)
        response = self.client.post(self.exam_url(), {
            f'choice_{self.question_one.id}': str(self.correct_one.id),
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Submission.objects.count(), 0)

    def test_nonexistent_course_returns_404(self):
        self.log_in()
        response = self.client.post(reverse('onlinecourse:submit', args=(999999,)), {})
        self.assertEqual(response.status_code, 404)

    def test_submission_cannot_be_seen_by_another_user(self):
        submission = Submission.objects.create(enrollment=self.enrollment)
        submission.choices.add(self.correct_one)
        self.log_in(self.other_user)

        response = self.client.get(self.result_url(submission.id))
        self.assertEqual(response.status_code, 404)

    def test_result_page_requires_login(self):
        submission = Submission.objects.create(enrollment=self.enrollment)
        response = self.client.get(self.result_url(submission.id))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/onlinecourse/login/', response['Location'])

    def test_reverse_submit_and_result_routes(self):
        self.assertEqual(self.exam_url(), f'/onlinecourse/{self.course.id}/submit/')
        self.assertEqual(
            self.result_url(42),
            f'/onlinecourse/{self.course.id}/submission/42/result/',
        )


class AssessmentAdminTests(AssessmentTestData):
    def test_assessment_and_course_models_are_registered(self):
        for model in (Course, Lesson, Instructor, Learner, Question, Choice, Submission):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)

    def test_admin_dashboard_shows_auth_and_onlinecourse(self):
        admin_user = User.objects.create_superuser(
            username='site-admin', email='admin@example.test', password='admin-test-password'
        )
        self.log_in(admin_user)
        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Authentication and Authorization')
        self.assertContains(response, 'OnlineCourse')

    def test_lesson_and_question_admin_inline_forms_load(self):
        admin_user = User.objects.create_superuser(
            username='site-admin', email='admin@example.test', password='admin-test-password'
        )
        self.log_in(admin_user)
        lesson_form = self.client.get(reverse('admin:onlinecourse_lesson_add'))
        question_form = self.client.get(reverse('admin:onlinecourse_question_add'))

        self.assertEqual(lesson_form.status_code, 200)
        self.assertEqual(question_form.status_code, 200)
        self.assertContains(lesson_form, 'question_set')
        self.assertContains(question_form, 'choice_set')
