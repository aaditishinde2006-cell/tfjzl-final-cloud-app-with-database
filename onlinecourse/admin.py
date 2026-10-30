
from django.contrib import admin

from .models import (
    Course,
    Lesson,
    Instructor,
    Learner,
    Question,
    Choice,
    Submission,
)


# Lesson inline
class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 5


# Choice inline
class ChoiceInline(admin.StackedInline):
    model = Choice
    extra = 4


# Question inline
class QuestionInline(admin.StackedInline):
    model = Question
    extra = 5


# Course admin
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline, QuestionInline]
    list_display = ('name', 'pub_date')
    list_filter = ['pub_date']
    search_fields = ['name', 'description']


# Lesson admin
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title']


# Question admin
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ['question_text', 'course', 'grade']
    list_filter = ['course']
    search_fields = ['question_text']


# Submission admin
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'enrollment']


# Register models
admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Instructor)
admin.site.register(Learner)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(Submission, SubmissionAdmin)
