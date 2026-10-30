from django.contrib import admin
from .models import Choice, Course, Instructor, Learner, Lesson, Question, Submission


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 0


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


# Register your models here.
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline]
    list_display = ('name', 'pub_date')
    list_filter = ['pub_date']
    search_fields = ['name', 'description']


class LessonAdmin(admin.ModelAdmin):
    list_display = ['title']
    inlines = [QuestionInline]


class QuestionAdmin(admin.ModelAdmin):
    list_display = ("content", "lesson", "grade")
    list_filter = ("lesson__course",)
    search_fields = ("content", "lesson__title", "lesson__course__name")
    inlines = [ChoiceInline]


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "enrollment", "submitted_at")
    list_filter = ("submitted_at",)
    readonly_fields = ("submitted_at",)

admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Instructor)
admin.site.register(Learner)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(Submission, SubmissionAdmin)
