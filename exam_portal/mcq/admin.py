from django.contrib import admin
from django.template.response import TemplateResponse
from django.db.models import Count, Q
from .models import MCQ, StudentAnswer, StudentProfile, Quiz, Category

# ✅ Register MCQ model
@admin.register(MCQ)
class MCQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'correct_option', 'quiz')
    search_fields = ('question',)

# ✅ Register Student Profile
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'roll_number', 'course')
    search_fields = ('user__username', 'roll_number', 'course')

# ✅ Custom Student Answer Dashboard
class StudentAnswerAdmin(admin.ModelAdmin):
    change_list_template = "admin/student_dashboard.html"
    list_display = ('student', 'question_summary', 'selected_option', 'is_correct')
    list_filter = ('student', 'is_correct')
    search_fields = ('student__username', 'question__question')

    def question_summary(self, obj):
        return obj.question.question[:100]
    question_summary.short_description = 'Question'

    def changelist_view(self, request, extra_context=None):
        student_stats = (
            StudentAnswer.objects
            .values('student__username')
            .annotate(
                total_attempts=Count('id'),
                correct_answers=Count('id', filter=Q(is_correct=True)),
                wrong_answers=Count('id', filter=Q(is_correct=False))
            )
        )
        context = {'student_stats': student_stats}
        return TemplateResponse(request, self.change_list_template, context)

# ✅ Register Quiz
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('quiz_title', 'category', 'duration', 'active', 'start_time', 'end_time')
    list_filter = ('active', 'category')
    search_fields = ('quiz_title',)

# ✅ Register Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

# ✅ Register StudentAnswer
admin.site.register(StudentAnswer, StudentAnswerAdmin)
