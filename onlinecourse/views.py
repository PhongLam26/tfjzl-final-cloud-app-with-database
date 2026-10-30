from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST
import logging

from .models import Choice, Course, Enrollment, Question, Submission

logger = logging.getLogger(__name__)
PASSING_SCORE_PERCENT = 80


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        if User.objects.filter(username=username).exists():
            context['message'] = 'User already exists.'
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
        login(request, user)
        return redirect('onlinecourse:index')


def login_request(request):
    context = {}
    if request.method == 'POST':
        user = authenticate(
            username=request.POST['username'],
            password=request.POST['psw'],
        )
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        context['message'] = 'Invalid username or password.'
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    return bool(user.is_authenticated and Enrollment.objects.filter(user=user, course=course).exists())


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_details_bootstrap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        user = self.request.user
        context['has_questions'] = Question.objects.filter(lesson__course=course).exists()
        context['is_enrolled'] = check_if_enrolled(user, course)
        return context


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    if user.is_authenticated and not check_if_enrolled(user, course):
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save(update_fields=['total_enrollment'])
    return HttpResponseRedirect(reverse('onlinecourse:course_details', args=(course.id,)))


@login_required
@require_POST
@transaction.atomic
def submit(request, course_id):
    """Validate and save the signed-in learner's answers for a course exam."""
    course = get_object_or_404(Course, pk=course_id)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    if enrollment is None:
        return HttpResponseForbidden('Enroll in this course before submitting its exam.')

    questions = list(
        Question.objects.filter(lesson__course=course).order_by('lesson__order', 'id')
    )
    if not questions:
        return HttpResponseBadRequest('This course does not have an exam yet.')

    expected_fields = {f'choice_{question.id}' for question in questions}
    submitted_fields = {key for key in request.POST if key.startswith('choice_')}
    if submitted_fields - expected_fields:
        return HttpResponseBadRequest('The submission contains an unknown question.')

    selected_choices = []
    for question in questions:
        values = request.POST.getlist(f'choice_{question.id}')
        if len(values) > 1:
            return HttpResponseBadRequest('Choose at most one answer for each question.')
        if not values or not values[0]:
            continue
        choice = Choice.objects.filter(pk=values[0], question=question).first()
        if choice is None:
            return HttpResponseBadRequest('An answer does not belong to its question.')
        selected_choices.append(choice)

    submission = Submission.objects.create(enrollment=enrollment)
    submission.choices.set(selected_choices)
    return redirect(
        'onlinecourse:show_exam_result',
        course_id=course.id,
        submission_id=submission.id,
    )


@login_required
def show_exam_result(request, course_id, submission_id):
    """Show a saved submission's weighted score and per-question feedback."""
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission.objects.select_related('enrollment__user', 'enrollment__course'),
        pk=submission_id,
        enrollment__user=request.user,
        enrollment__course=course,
    )
    questions = list(
        Question.objects.filter(lesson__course=course)
        .order_by('lesson__order', 'id')
        .prefetch_related('choice_set')
    )
    selected_by_question = {}
    for choice in submission.choices.filter(
        question__lesson__course=course
    ).select_related('question').order_by('id'):
        selected_by_question.setdefault(choice.question_id, []).append(choice)

    question_results = []
    score = 0
    possible = sum(question.grade for question in questions)
    for question in questions:
        selected_question_choices = selected_by_question.get(question.id, [])
        selected_choice = selected_question_choices[0] if selected_question_choices else None
        correct_choices = [choice for choice in question.choice_set.all() if choice.is_correct]
        selected_question_ids = [choice.id for choice in selected_question_choices]
        is_correct = question.is_get_score(selected_question_ids)
        if is_correct:
            score += question.grade
        question_results.append({
            'question': question,
            'selected_choice': selected_choice,
            'correct_choices': correct_choices,
            'is_correct': is_correct,
        })

    grade = round((score / possible) * 100, 1) if possible else 0
    selected_ids = sorted(
        choice.id
        for choices in selected_by_question.values()
        for choice in choices
    )
    context = {
        'course': course,
        'submission': submission,
        'question_results': question_results,
        'score': score,
        'possible': possible,
        'total_score': possible,
        'grade': grade,
        'selected_ids': selected_ids,
        'passed': grade >= PASSING_SCORE_PERCENT and possible > 0,
        'passing_score_percent': PASSING_SCORE_PERCENT,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
