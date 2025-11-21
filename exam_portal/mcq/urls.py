from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Public & Dashboard ---
    path('', views.home, name='home'),                          # Public welcome page
    path('dashboard_redirect/', views.dashboard_redirect, name='dashboard_redirect'),
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),

    # --- Admin Views ---
    path('admin_home/', views.admin_home, name='admin_home'),
    path('custom_admin/', views.custom_admin_dashboard, name='custom_admin'),
    path('upload/', views.upload_mcq, name='upload_mcq'),
    path('students/', views.all_students, name='all_students'),
    path('students/<int:student_id>/results/', views.admin_view_results, name='admin_view_results'),
    path('manage-categories/', views.manage_categories, name='manage_categories'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('delete-quiz/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    path('admin_download_pdf/<int:student_id>/<int:quiz_id>/', views.admin_download_quiz_pdf, name='admin_download_quiz_pdf'),

    # --- Staff Quiz Management ---
    path('staff/quiz-management/', views.staff_quiz_management, name='staff_quiz_management'),
    path('staff/quiz/<int:quiz_id>/activate/', views.activate_quiz, name='activate_quiz'),
    path('staff/quiz/<int:quiz_id>/deactivate/', views.deactivate_quiz, name='deactivate_quiz'),
    path('staff/quiz/<int:quiz_id>/edit/', views.edit_quiz, name='edit_quiz'),
    path('staff/quiz/<int:quiz_id>/delete/', views.delete_quiz, name='delete_quiz'),

    # --- Student Features ---
    path('dashboard/', views.student_dashboard, name='student_dashboard'),  # Redundant but kept for URL route consistency
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('attempt/<int:quiz_id>/', views.attempt_quiz, name='attempt_quiz'),
    path('quiz_result/', views.quiz_result, name='quiz_result'),
    path('quiz_result/<int:quiz_id>/', views.quiz_result, name='quiz_result_with_id'),
    path('quiz_result/<int:quiz_id>/details/', views.quiz_detail_result, name='quiz_detail_result'),
    path('view-results/', views.view_results, name='view_results'),
    path('my_results/', views.view_results, name='my_results'),
    path('download_quiz_pdf/<int:quiz_id>/', views.download_quiz_pdf, name='download_quiz_pdf'),

    # --- Authentication ---
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='mcq/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
]
