from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Category, Quiz


# ✅ Upload Form (Categorized MCQ Upload)
class UploadFileForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=True,
        label="Select Category",
        widget=forms.Select(
            attrs={'class': 'form-select'}
        )
    )
    quiz_title = forms.CharField(
        max_length=255,
        required=True,
        label="Quiz Title",
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Enter quiz title'}
        )
    )
    file = forms.FileField(
        label="Select Word File (.docx)",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):   # ✅ now properly inside class
        super().__init__(*args, **kwargs)
        # Add a visible placeholder for the dropdown
        self.fields['category'].empty_label = "Select Category"


# ✅ Student Registration Form
class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']


# ✅ Quiz Management Form (for staff dashboard)
class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['category', 'quiz_title', 'start_time', 'end_time', 'duration', 'active', 'upload_file']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Duration in minutes'
            }),
            'quiz_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter quiz title'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'upload_file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 👇 Add a default "Select Category" placeholder
        self.fields['category'].empty_label = "Select Category"

        
