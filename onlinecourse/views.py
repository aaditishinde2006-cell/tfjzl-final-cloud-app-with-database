
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging

from .models import Course, Enrollment, Question, Choice, Submission

# Get an instance of a logger
logger = logging.getLogger(__name__)


# User registration
def registration_request(request):
    context = {}

    if request.method == 'GET':
        return render(
            request,
            'onlinecourse/user_registration_bootstrap.html',
            context
        )

    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']

        user_exist = False

        try:
            User.objects.get(username=username)
            user_exist = True
        except User.DoesNotExist:
            logger.error("New user")

        if not user_exist:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password
            )

            login(request, user)
            return redirect("onlinecourse:index")

        else:
            context['message'] = "User already exists."

            return render(
                request,
                'onlinecourse/user_registration_bootstrap.html',
                context
            )


# User login
def login_request(request):
    context = {}

    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']

        user = authenticate(
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')

        else:
            context['message'] = "Invalid username or password."

            return render(
                request,
                'onlinecourse/user_login_bootstrap.html',
                context
            )

    else:
        return render(
            request,
            'onlinecourse/user_login_bootstrap.html',
            context
        )


# User logout
def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


# Check whether user is enrolled
def check_if_enrolled(user, course):
    is_enrolled = False

    if user.id is not None:
        num_results = Enrollment.objects.filter(
            user=user,
            course=course
        ).count()

        if num_results > 0:
            is_enrolled = True

    return is_enrolled


# Course list view
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user

        courses = Course.objects.order_by(
            '-total_enrollment'
        )[:10]

        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(
                    user,
                    course
                )

        return courses


# Course detail view
class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


# Enroll in course
def enroll(request, course_id):
    course = get_object_or_404(
        Course,
        pk=course_id
    )

    user = request.user

    is_enrolled = check_if_enrolled(
        user,
        course
    )

    if not is_enrolled and user.is_authenticated:

        Enrollment.objects.create(
            user=user,
            course=course,
            mode='honor'
        )

        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse(
            viewname='onlinecourse:course_details',
            args=(course.id,)
        )
    )


# Extract selected answers from exam form
def extract_answers(request):
    submitted_answers = []

    for key in request.POST:

        if key.startswith('choice'):

            values = request.POST.getlist(key)

            for value in values:

                if value.isdigit():
                    submitted_answers.append(int(value))

    return submitted_answers


# Submit exam
def submit(request, course_id):

    course = get_object_or_404(
        Course,
        pk=course_id
    )

    if not request.user.is_authenticated:
        return redirect('onlinecourse:login')

    if request.method != 'POST':
        return redirect(
            'onlinecourse:course_details',
            pk=course.id
        )

    # Get the user's enrollment
    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course=course
    )

    # Create submission
    submission = Submission.objects.create(
        enrollment=enrollment
    )

    # Get selected answers
    selected_answers = extract_answers(request)

    # Only accept choices belonging to this course
    valid_choices = Choice.objects.filter(
        id__in=selected_answers,
        question__course=course
    )

    # Save selected choices
    submission.choices.add(*valid_choices)

    # Redirect to result page
    return redirect(
        'onlinecourse:show_exam_result',
        course_id=course.id,
        submission_id=submission.id
    )


# Show exam result
def show_exam_result(request, course_id, submission_id):

    # Check authentication
    if not request.user.is_authenticated:
        return redirect('onlinecourse:login')

    course = get_object_or_404(
        Course,
        pk=course_id
    )

    # Get submission belonging to this course and current user
    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__course=course,
        enrollment__user=request.user
    )

    # Get all course questions
    questions = Question.objects.filter(
        course=course
    ).prefetch_related('choice_set')

    # Get selected choice IDs
    selected_ids = list(
        submission.choices.values_list(
            'id',
            flat=True
        )
    )

    total_score = 0
    total_grade = 0
    question_results = []

    # Calculate each question's result
    for question in questions:

        total_grade += question.grade

        selected_for_question = [
            choice_id
            for choice_id in selected_ids
            if question.choice_set.filter(
                id=choice_id
            ).exists()
        ]

        question_score = question.is_get_score(
            selected_for_question
        )

        total_score += question_score

        question_results.append({
            'question': question,
            'selected_choices': question.choice_set.filter(
                id__in=selected_for_question
            ),
            'correct_choices': question.choice_set.filter(
                is_correct=True
            ),
            'score': question_score,
            'grade': question.grade,
        })

    # Calculate percentage
    percentage = (
        (total_score / total_grade) * 100
        if total_grade > 0
        else 0
    )

    # Prepare template context
    context = {
    'course': course,
    'submission': submission,
    'questions': questions,
    'question_results': question_results,
    'score': total_score,
    'total_score': total_score,
    'total_grade': total_grade,
    'possible_score': total_grade,
    'total': total_grade,
    'correct': total_score,
    'grade': percentage,
    'percentage': percentage,
}
    return render(
        request,
        'onlinecourse/exam_result_bootstrap.html',
        context
    )
