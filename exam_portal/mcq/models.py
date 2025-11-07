from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django import forms


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)  # recently added

    def __str__(self):
        return self.name


class Quiz(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    quiz_title = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(help_text="Enter duration in minutes", null=True, blank=True)
    active = models.BooleanField(default=True)
    upload_file = models.FileField(upload_to="mcq_uploads/", null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)  # <— this is required

    def __str__(self):
        return f"{self.quiz_title} ({self.category})"


class MCQ(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True, related_name='questions')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    question = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1)

    def __str__(self):
        return self.question[:50]


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=20)
    course = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username


class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(MCQ, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.username} - {self.question.id}"


class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mcq = models.ForeignKey('MCQ', on_delete=models.CASCADE)
    correct_answers = models.IntegerField(default=0)
    wrong_answers = models.IntegerField(default=0)
    score = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user.username} - Score: {self.score}"
    
class QuizAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE)
    score = models.FloatField()
    correct_answers = models.IntegerField()
    wrong_answers = models.IntegerField()
    total_questions = models.IntegerField()
    date_attempted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.quiz.quiz_title}"