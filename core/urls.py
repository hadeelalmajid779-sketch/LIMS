# core/urls.py
from django.urls import path
from . import views
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'core'

urlpatterns = [

    # الصفحة الرئيسية (الأزرار)
    path('', views.home, name='home'),

    # تسجيل الدخول حسب الدور
    path('login/<str:role>/', views.role_login, name='role_login'),

    # تسجيل الدخول العام (إذا تحتاجينه)
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='core:login'), name='logout'),

    # Dashboards
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('accounting/dashboard/', views.accounting_dashboard, name='accounting_dashboard'),
    path('lab/dashboard/', views.lab_dashboard, name='lab_dashboard'),
    
    path('', views.dashboard, name='dashboard'),
    path('', views.patient_list, name='home'),
    path('patient/', views.patient_list, name='patient_list'),
    path('patient/new/', views.patient_create, name='patient_create'),
    path('patient/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patient/<int:pk>/edit/', views.patient_update, name='patient_update'),
    path('patient/<int:pk>/delete/', views.patient_delete, name='patient_delete'),


    # Tests
    path('test/', views.test_list, name='test_list'),
    path('test/add/', views.test_create, name='test_create'),
    path('test/<int:pk>/edit/', views.test_detail, name='test_edit'),
    path('test/<int:pk>/', views.test_detail, name='test_detail'),
    path('test/<int:pk>/delete/', views.test_delete, name='test_delete'),

    # Patient Tests (results)
    path('patienttest/', views.patienttest_list, name='patienttest_list'),
    path('patienttest/<int:pk>/',views.patienttest_detail, name='patienttest_detail'),
    path('patienttest/new/', views.patienttest_create, name='patienttest_create'),
    path('patienttest/<int:pk>/delete/', views.patienttest_delete, name='patienttest_delete'),
    path('patienttest/<int:pk>/', views.patienttest_detail, name='patienttest_detail'),
    path('testresult/add/<int:pk>/', views.testresult_create, name='testresult_create'),
    path('testresult/delete/<int:pk>/', views.testresult_delete, name='testresult_delete'),
    path('testresult/<int:pk>/', views.testresult_detail, name='testresult_detail'),
    path('testresult/<int:pk>/update/', views.testresult_update, name='testresult_update'),
    path( 'testresult/<int:pk>/approve/', views.testresult_approve, name='testresult_approve'),
    path( 'testresult/<int:pk>/complete/',views.testresult_complete, name='testresult_complete'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('testresult/', views.testresult_list, name='testresult_list'),
    path('testresult/<int:pk>/print/', views.testresult_print, name='testresult_print'),

    path('login/', views.UserLoginView.as_view(), name='login'),
    

    path('reception/', views.reception_dashboard, name='reception_dashboard'),
    path('laboratory/',views. lab_dashboard, name='lab_dashboard'),
    path('accounting/', views.accounting_dashboard, name='accounting_dashboard'),
    path('', views.UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='core:login'), name='logout'),
    path('redirect/', views.redirect_dashboard, name='redirect_dashboard'),
    path('testresult/<int:pk>/pdf/', views.testresult_pdf, name='testresult_pdf'),
    path('manager/export/', views.export_manager_report, name='export_manager_report'),
    path('manager/pdf/', views.export_manager_pdf, name='export_manager_pdf'),
]
