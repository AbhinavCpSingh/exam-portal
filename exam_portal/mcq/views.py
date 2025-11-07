from django.shortcuts import render, redirect
from django.http import HttpResponse
from docx import Document
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
import re
from .models import MCQ, StudentAnswer, Quiz, Category, QuizAttempt
from .forms import UploadFileForm
from .models import *
from django.contrib import messages
from django.contrib.auth import login
from .forms import StudentRegistrationForm
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404
from .models import StudentAnswer
from django.contrib.auth.models import User
from .models import Result
from django.contrib.auth.models import Group
import random
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils import timezone
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import QuizForm
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from django.conf import settings
import os

@login_required
def home(request):
    if request.user.is_staff:
        return redirect('admin_home')
    else:
        return redirect('student_dashboard')

    
@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_home(request):
    return render(request, 'mcq/admin_home.html', {'user': request.user})


@staff_member_required
def custom_admin_dashboard(request):
    return render(request, 'mcq/custom_admin.html')

def register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = False  # ensure student role
            user.save()

            # Optionally, add to "Students" group (for permissions)
            student_group, created = Group.objects.get_or_create(name='Students')
            user.groups.add(student_group)

            # Automatically log the user in
            login(request, user)

            # Redirect to student dashboard (not admin)
            return redirect('student_dashboard')
    else:
        form = StudentRegistrationForm()

    return render(request, 'mcq/register.html', {'form': form})


@staff_member_required
def upload_mcq(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = form.cleaned_data["file"]
                category = form.cleaned_data["category"]
                quiz_title = form.cleaned_data["quiz_title"]

                # ✅ Check if a Quiz already exists for this title/category
                quiz, created = Quiz.objects.get_or_create(
                    category=category,
                    quiz_title=quiz_title,
                    defaults={'active': False, 'created_by': request.user}
                )


                doc = Document(file)
                question_text = ""
                option_a = option_b = option_c = option_d = ""
                correct_option = ""

                for para in doc.paragraphs:
                    text = para.text.strip()
                    if not text:
                        continue

                    parts = re.split(r'(?=\s[A-D]\.)|(?=\sAnswer:)', text)
                    for part in parts:
                        part = part.strip()
                        if not part:
                            continue

                        if part.startswith("Q."):
                            if question_text:
                                MCQ.objects.create(
                                    quiz=quiz,             # ✅ Link to Quiz
                                    category=category,
                                    question=question_text.strip(),
                                    option_a=option_a.strip(),
                                    option_b=option_b.strip(),
                                    option_c=option_c.strip(),
                                    option_d=option_d.strip(),
                                    correct_option=correct_option.strip()
                                )
                            question_text = part[2:].strip()
                            option_a = option_b = option_c = option_d = ""
                            correct_option = ""
                        elif part.startswith("A."):
                            option_a = part[2:].strip()
                        elif part.startswith("B."):
                            option_b = part[2:].strip()
                        elif part.startswith("C."):
                            option_c = part[2:].strip()
                        elif part.startswith("D."):
                            option_d = part[2:].strip()
                        elif part.startswith("Answer:"):
                            correct_option = part.replace("Answer:", "").strip()[0].upper()

                # Save the last question
                if question_text:
                    MCQ.objects.create(
                        quiz=quiz,             # ✅ Link to Quiz
                        category=category,
                        question=question_text.strip(),
                        option_a=option_a.strip(),
                        option_b=option_b.strip(),
                        option_c=option_c.strip(),
                        option_d=option_d.strip(),
                        correct_option=correct_option.strip()
                    )

                messages.success(
                    request,
                    f"✅ Questions uploaded and linked to quiz '{quiz_title}' under category '{category.name}' successfully!"
                )
                return redirect("upload_mcq")

            except Exception as e:
                messages.error(request, f"⚠️ Error while processing file: {e}")
                return redirect("upload_mcq")
    else:
        form = UploadFileForm()

    return render(request, "mcq/upload.html", {"form": form})



def custom_logout(request):
    logout(request)              # Logs out the user
    request.session.flush()      # Clears the session data
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')     # Redirects to the login page


@login_required
def student_dashboard(request):
    quizzes = Quiz.objects.filter(active=True)
    total_quizzes = quizzes.count()

    # Fixed lookup for related quiz via question__quiz
    attempted_quizzes = StudentAnswer.objects.filter(student=request.user).values_list('question__quiz', flat=True).distinct().count()

    if total_quizzes > 0:
        progress = round((attempted_quizzes / total_quizzes) * 100, 2)
    else:
        progress = 0

    latest_quiz = quizzes.last()

    return render(request, 'mcq/student_dashboard.html', {
        'quizzes': quizzes,
        'total_quizzes': total_quizzes,
        'attempted_quizzes': attempted_quizzes,
        'progress': progress,
        'quiz': latest_quiz,
    })


@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    now = timezone.now()
    if now < quiz.start_time:
        return render(request, 'mcq/quiz_not_started.html', {'quiz': quiz})
    elif now > quiz.end_time:
        return render(request, 'mcq/quiz_expired.html', {'quiz': quiz})

    # Show disclaimer before starting
    if request.method == 'POST':
        # Mark session as started properly
        request.session['quiz_started'] = True
        return redirect('attempt_quiz', quiz_id=quiz.id)

    return render(request, 'mcq/quiz_disclaimer.html', {'quiz': quiz})


@login_required
def attempt_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Prevent direct access without starting properly
    if not request.session.get('quiz_started'):
        messages.warning(request, "⚠️ You must start the quiz properly from the Start page.")
        return redirect('start_quiz', quiz_id=quiz.id)

    # Time control — only allow during valid quiz window
    now = timezone.now()
    if now < quiz.start_time:
        messages.warning(request, "⏳ This quiz hasn’t started yet.")
        return redirect('start_quiz', quiz_id=quiz.id)
    elif now > quiz.end_time:
        messages.error(request, "❌ This quiz has expired.")
        return redirect('my_results')  # redirect to results page

    # Retrieve randomized questions
    questions = quiz.questions.all().order_by('?')

    # Store start and end time in session (for auto submission logic)
    if 'quiz_end_time' not in request.session:
        request.session['quiz_end_time'] = (now + timezone.timedelta(minutes=quiz.duration)).isoformat()

    end_time = timezone.datetime.fromisoformat(request.session['quiz_end_time'])

    # Handle submission
    if request.method == 'POST':
        for question in questions:
            selected = request.POST.get(str(question.id))
            if selected:
                is_correct = (selected == question.correct_option)
                StudentAnswer.objects.update_or_create(
                    student=request.user,
                    question=question,
                    defaults={'selected_option': selected, 'is_correct': is_correct}
                )
        # Clean up session variables
        request.session.pop('quiz_started', None)
        request.session.pop('quiz_end_time', None)

        # ✅ Redirect to student result summary page
        return redirect('my_results')

    return render(request, 'mcq/attempt_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'end_time': end_time,
        'duration': quiz.duration
    })


# Show results for a specific student
@login_required
def view_results(request):
    student = request.user

    # ✅ Find all distinct quizzes this student has answered
    quizzes = Quiz.objects.filter(
        questions__studentanswer__student=student
    ).distinct()

    quiz_results = []

    for quiz in quizzes:
        # All answers by this student for that quiz
        answers = StudentAnswer.objects.filter(
            student=student,
            question__quiz=quiz
        )

        total_questions = answers.count()
        correct_answers = answers.filter(is_correct=True).count()
        wrong_answers = total_questions - correct_answers
        score = round((correct_answers / total_questions) * 100, 2) if total_questions > 0 else 0

        quiz_results.append({
            'quiz': quiz,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers,
            'score': score
        })

    return render(request, 'mcq/student_results.html', {
        'quiz_results': quiz_results
    })


@staff_member_required
def all_students(request):
    """Show all students with calculated results from StudentAnswer."""
    students = User.objects.filter(is_staff=False)

    student_data = []
    for student in students:
        answers = StudentAnswer.objects.filter(student=student)

        total_attempts = answers.count()
        correct_answers = answers.filter(is_correct=True).count()
        wrong_answers = answers.filter(is_correct=False).count()

        student_data.append({
            'student': student,
            'total_attempts': total_attempts,
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers
        })

    return render(request, 'mcq/all_students.html', {'student_data': student_data})


@login_required
def admin_view_results(request, student_id):
    from .models import StudentAnswer
    from django.contrib.auth.models import User

    student = get_object_or_404(User, id=student_id)
    student_answers = StudentAnswer.objects.filter(student=student).select_related('question')

    if not student_answers.exists():
        return render(request, "mcq/admin_view_results.html", {
            "student": student,
            "no_results": True
        })

    quiz_data = {}
    for ans in student_answers:
        quiz = ans.question.quiz  # get quiz from the related question
        if quiz.id not in quiz_data:
            quiz_data[quiz.id] = {
                "quiz": quiz,
                "total_questions": 0,
                "correct_answers": 0,
                "wrong_answers": 0,
                "questions": []
            }

        quiz_data[quiz.id]["total_questions"] += 1
        is_correct = ans.selected_option == ans.question.correct_option
        if is_correct:
            quiz_data[quiz.id]["correct_answers"] += 1
        else:
            quiz_data[quiz.id]["wrong_answers"] += 1

        quiz_data[quiz.id]["questions"].append({
            "question": ans.question.question,
            "selected_option": ans.selected_option,
            "correct_option": ans.question.correct_option,
            "is_correct": is_correct
        })

    # calculate percentage and pass/fail status
    for qid, qd in quiz_data.items():
        qd["score"] = round((qd["correct_answers"] / qd["total_questions"]) * 100, 2) if qd["total_questions"] > 0 else 0

    return render(request, "mcq/admin_view_results.html", {
        "student": student,
        "quiz_results": quiz_data.values()
    })


@login_required
def admin_download_quiz_pdf(request, student_id, quiz_id):
    from io import BytesIO
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    from django.conf import settings
    import os

    quiz = get_object_or_404(Quiz, id=quiz_id)
    student = get_object_or_404(User, id=student_id)
    answers = StudentAnswer.objects.filter(student=student, question__quiz=quiz).select_related('question')

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ====== HEADER (CDAC NOIDA STYLE) ======
    cdac_blue = colors.HexColor("#002B5B")
    p.setFillColor(cdac_blue)
    p.rect(0, height - 100, width, 100, fill=True, stroke=False)

    # ✅ Logo (Optional)
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'cdac_logo.png')
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        p.drawImage(logo, 40, height - 90, width=70, height=70, mask='auto')

    # Title
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(170, height - 45, "CDAC NOIDA EXAM PORTAL")

    p.setFont("Helvetica", 12)
    p.drawString(135, height - 75, f"Quiz Title: {quiz.quiz_title}")
    p.drawString(400, height - 75, f"Category: {quiz.category.name}")

    # Divider line
    p.setStrokeColor(colors.HexColor("#0066cc"))
    p.setLineWidth(2)
    p.line(40, height - 110, width - 40, height - 110)

    # ====== STUDENT INFORMATION ======
    y = height - 140
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    p.drawString(50, y, f"Student Name: {student.get_full_name() or student.username}")
    y -= 20
    p.drawString(50, y, f"Email: {student.email or 'N/A'}")

    # ====== QUIZ SUMMARY ======
    total = answers.count()
    correct = answers.filter(is_correct=True).count()
    wrong = total - correct
    percentage = round((correct / total) * 100, 2) if total else 0
    result_status = "PASS" if percentage >= 50 else "FAIL"

    y -= 40
    p.setFillColor(colors.HexColor("#e8f0fc"))
    p.roundRect(40, y - 130, width - 80, 120, 12, fill=True, stroke=False)

    p.setFillColor(cdac_blue)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(60, y - 35, "📊 Quiz Performance Summary")

    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    p.drawString(80, y - 60, f"Total Questions: {total}")
    p.drawString(80, y - 80, f"Correct Answers: {correct}")
    p.drawString(80, y - 100, f"Wrong Answers: {wrong}")
    p.drawString(300, y - 60, f"Score: {percentage}%")

    if result_status == "PASS":
        p.setFillColor(colors.green)
    else:
        p.setFillColor(colors.red)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(300, y - 80, f"Result: {result_status}")

    # ====== DETAILED ANSWERS ======
    y -= 160
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(cdac_blue)
    p.drawString(50, y, "🧾 Detailed Answers:")
    y -= 25

    p.setFont("Helvetica", 11)
    for idx, ans in enumerate(answers, start=1):
        question_text = ans.question.question
        if len(question_text) > 90:
            question_text = question_text[:90] + "..."

        # Question
        p.setFillColor(colors.black)
        p.drawString(50, y, f"{idx}. {question_text}")
        y -= 15

        # Student Answer
        p.setFillColor(colors.HexColor("#222222"))
        p.drawString(65, y, f"Student's Answer: {ans.selected_option or '-'}")
        y -= 15

        # Correct / Wrong Status
        if ans.is_correct:
            p.setFillColor(colors.HexColor("#004d00"))  # dark green
            status = "✓ Correct"
        else:
            p.setFillColor(colors.HexColor("#8B0000"))  # dark red
            status = "✗ Wrong"

        p.setFont("Helvetica-Bold", 11)
        p.drawString(65, y, f"Correct Answer: {ans.question.correct_option}   |   Status: {status}")
        y -= 25
        p.setFont("Helvetica", 11)

        if y < 100:
            p.showPage()
            p.setFont("Helvetica-Bold", 14)
            p.setFillColor(cdac_blue)
            p.drawString(50, height - 60, "🧾 Detailed Answers (continued)")
            y = height - 100
            p.setFont("Helvetica", 11)

    # ====== FOOTER ======
    p.setStrokeColor(colors.HexColor("#0066cc"))
    p.line(40, 70, width - 40, 70)

    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.grey)
    p.drawString(50, 55, "Generated by CDAC Noida Exam Portal © 2025")
    p.drawRightString(width - 50, 55, "Authorized Signature: ___________________")

    # ====== SAVE ======
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=\"{student.username}_{quiz.quiz_title}_CDAC_Report.pdf\"'
    return response
 


@login_required
def quiz_detail_result(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    student = request.user

    # Get all answers of this student for this quiz
    answers = StudentAnswer.objects.filter(
        student=student,
        question__quiz=quiz
    ).select_related('question')

    if not answers.exists():
        messages.warning(request, "⚠️ No answers found for this quiz.")
        return redirect('my_results')

    total_questions = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    wrong_answers = total_questions - correct_answers
    score = round((correct_answers / total_questions) * 100, 2) if total_questions > 0 else 0

    return render(request, 'mcq/quiz_detail_result.html', {
        'quiz': quiz,
        'answers': answers,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
        'score': score,
    })


@login_required
def quiz_result(request, quiz_id=None):
    student = request.user

    # ✅ Use correct field name: `active`, not `is_active`
    if quiz_id:
        quiz = get_object_or_404(Quiz, id=quiz_id)
        answers = StudentAnswer.objects.filter(student=student, question__quiz=quiz).select_related('question')
    else:
        # fallback: latest active quiz
        quiz = Quiz.objects.filter(active=True).last()
        answers = StudentAnswer.objects.filter(student=student).select_related('question')

    # Handle edge cases: no quiz or no answers
    if not quiz:
        messages.warning(request, "⚠ No quiz found or available.")
        return redirect('student_dashboard')

    total_questions = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    wrong_answers = total_questions - correct_answers
    attempted_questions = total_questions

    return render(request, 'mcq/quiz_result.html', {
        'quiz': quiz,
        'answers': answers,
        'total_questions': total_questions,
        'attempted_questions': attempted_questions,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
    })


# Show list of all students who have results
@staff_member_required
def student_list(request):
    students = User.objects.filter(studentanswer__isnull=False).distinct()
    return render(request, 'mcq/student_list.html', {'students': students})


@login_required
def download_quiz_pdf(request, quiz_id):
    quiz = Quiz.objects.get(id=quiz_id)
    answers = StudentAnswer.objects.filter(student=request.user, question__quiz=quiz).select_related('question')

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ====== HEADER (CDAC NOIDA STYLE) ======
    cdac_blue = colors.HexColor("#002B5B")
    p.setFillColor(cdac_blue)
    p.rect(0, height - 100, width, 100, fill=True, stroke=False)

    # ✅ Logo (Optional)
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'cdac_logo.png')
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        p.drawImage(logo, 40, height - 90, width=70, height=70, mask='auto')

    # Title
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(170, height - 45, "CDAC NOIDA EXAM PORTAL")

    p.setFont("Helvetica", 12)
    p.drawString(135, height - 75, f"Quiz Title: {quiz.quiz_title}")
    p.drawString(400, height - 75, f"Category: {quiz.category.name}")

    # Divider line
    p.setStrokeColor(colors.HexColor("#0066cc"))
    p.setLineWidth(2)
    p.line(40, height - 110, width - 40, height - 110)

    # ====== STUDENT INFORMATION ======
    y = height - 140
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    p.drawString(50, y, f"Student Name: {request.user.get_full_name() or request.user.username}")
    y -= 20
    p.drawString(50, y, f"Email: {request.user.email}")

    # ====== QUIZ SUMMARY ======
    total = answers.count()
    correct = answers.filter(is_correct=True).count()
    wrong = total - correct
    percentage = round((correct / total) * 100, 2) if total else 0
    result_status = "PASS" if percentage >= 50 else "FAIL"

    y -= 40
    p.setFillColor(colors.HexColor("#e8f0fc"))
    p.roundRect(40, y - 130, width - 80, 120, 12, fill=True, stroke=False)

    p.setFillColor(cdac_blue)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(60, y - 35, "📊 Quiz Performance Summary")

    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    p.drawString(80, y - 60, f"Total Questions: {total}")
    p.drawString(80, y - 80, f"Correct Answers: {correct}")
    p.drawString(80, y - 100, f"Wrong Answers: {wrong}")
    p.drawString(300, y - 60, f"Score: {percentage}%")

    if result_status == "PASS":
        p.setFillColor(colors.green)
    else:
        p.setFillColor(colors.red)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(300, y - 80, f"Result: {result_status}")

    # ====== DETAILED ANSWERS ======
    y -= 160
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(cdac_blue)
    p.drawString(50, y, "🧾 Detailed Answers:")
    y -= 25

    p.setFont("Helvetica", 11)
    for idx, ans in enumerate(answers, start=1):
        question_text = ans.question.question
        if len(question_text) > 90:
            question_text = question_text[:90] + "..."

        # Question
        p.setFillColor(colors.black)
        p.drawString(50, y, f"{idx}. {question_text}")
        y -= 15

        # Student Answer
        p.setFillColor(colors.HexColor("#222222"))
        p.drawString(65, y, f"Your Answer: {ans.selected_option or '-'}")
        y -= 15

        # Correct / Wrong Status — dark bold colors
        if ans.is_correct:
            p.setFillColor(colors.HexColor("#004d00"))  # dark green
            status = "✓ Correct"
        else:
            p.setFillColor(colors.HexColor("#8B0000"))  # dark red
            status = "✗ Wrong"

        p.setFont("Helvetica-Bold", 11)
        p.drawString(65, y, f"Correct Answer: {ans.question.correct_option}   |   Status: {status}")
        y -= 25
        p.setFont("Helvetica", 11)

        if y < 100:
            p.showPage()
            p.setFont("Helvetica-Bold", 14)
            p.setFillColor(cdac_blue)
            p.drawString(50, height - 60, "🧾 Detailed Answers (continued)")
            y = height - 100
            p.setFont("Helvetica", 11)

    # ====== FOOTER ======
    p.setStrokeColor(colors.HexColor("#0066cc"))
    p.line(40, 70, width - 40, 70)

    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.grey)
    p.drawString(50, 55, "Generated by CDAC Noida Exam Portal © 2025")
    p.drawRightString(width - 50, 55, "Authorized Signature: ___________________")

    # ====== SAVE ======
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=\"{quiz.quiz_title}_CDAC_Report.pdf\"'
    return response


@staff_member_required
def manage_categories(request):
    categories = Category.objects.all().order_by('name')

    if request.method == "POST":
        new_category = request.POST.get("category_name").strip()
        if new_category:
            Category.objects.get_or_create(name=new_category)
            messages.success(request, f"✅ Category '{new_category}' added successfully!")
        else:
            messages.warning(request, "⚠️ Please enter a valid category name.")
        return redirect('manage_categories')

    return render(request, "mcq/manage_categories.html", {"categories": categories})


@staff_member_required
def delete_category(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
        category.delete()
        messages.success(request, f"🗑️ Category '{category.name}' deleted successfully!")
    except Category.DoesNotExist:
        messages.error(request, "⚠️ Category not found.")
    return redirect('manage_categories')


@staff_member_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.delete()
    messages.success(request, "🗑️ Quiz deleted successfully.")
    return redirect('staff_quiz_management')

# Staff access check
def staff_required(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(staff_required)
def staff_quiz_management(request):
    quizzes = Quiz.objects.filter(created_by=request.user)
    
    if request.method == 'POST':
        form = QuizForm(request.POST, request.FILES)
        
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = request.user   # ✅ Add this line
            quiz.save()
            messages.success(request, "✅ Quiz created successfully!")
            return redirect('staff_quiz_management')

    else:
        form = QuizForm()
    
    return render(request, 'staff/quiz_management.html', {'form': form, 'quizzes': quizzes})


@login_required
@user_passes_test(staff_required)
def activate_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.active = True
    quiz.save()
    messages.success(request, f"✅ Quiz '{quiz.quiz_title}' activated successfully!")
    return redirect('staff_quiz_management')   # ✅ Correct redirect name


@login_required
@user_passes_test(staff_required)
def deactivate_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.active = False
    quiz.save()
    messages.warning(request, f"⚠️ Quiz '{quiz.quiz_title}' deactivated.")
    return redirect('staff_quiz_management')   # ✅ same fix

@login_required
@user_passes_test(staff_required)
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.delete()
    messages.success(request, f"🗑 Quiz '{quiz.quiz_title}' deleted successfully!")
    return redirect('staff_quiz_management')  # ✅ Correct name here

@login_required
@user_passes_test(staff_required)
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == 'POST':
        form = QuizForm(request.POST, request.FILES, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Quiz updated successfully!")
            return redirect('staff_quiz_management')  # ✅ correct redirect
    else:
        form = QuizForm(instance=quiz)
    return render(request, 'staff/edit_quiz.html', {'form': form, 'quiz': quiz})
