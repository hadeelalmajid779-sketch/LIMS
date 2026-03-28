
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import  Test, PatientTest, ActivityLog
from .forms import   PatientTestForm, TestForm  
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from core.models import TestResult, LabOrder, ParameterResult
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db.models.functions import TruncMonth
from django.db.models import Sum
import json

def home(request):
    return render(request, 'core/home.html')

def is_doctor(user):
    return user.groups.filter(name='Doctor').exists()

def pending_results_count(request):
    if request.user.is_authenticated:
        return {
            'pending_results_count': TestResult.objects.filter(status='pending').count()
        }
    return {}

from django.shortcuts import render, get_object_or_404, redirect
from .models import Patient
from .forms import PatientForm

def patient_list(request):
    patients = Patient.objects.all()
    return render(request, 'core/patient_list.html', {'patients': patients})


def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('core:patient_list')
    else:
        form = PatientForm()
    return render(request, 'core/patient_form.html', {'form': form})


def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('core:patient_list')
    else:
        form = PatientForm(instance=patient)
    return render(request, 'core/patient_form.html', {'form': form})

def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patienttest = PatientTest.objects.filter(patient=patient)

    return render(request, 'core/patient_detail.html', {
        'patient': patient,
        'patienttest': patienttest
    })



def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        return redirect('core:patient_list')
    return render(request, 'core/patient_confirm_delete.html', {'patient': patient})
# Tests
def test_list(request):
    test = Test.objects.order_by('department', 'test_name')
    return render(request, 'core/test_list.html', {'test': test})

def test_create(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save()
            return redirect(reverse('core:test_detail', kwargs={'pk': test.pk}))
    else:
        form = TestForm()
    return render(request, 'core/test_form.html', {'form': form, 'action': 'Create'})

def test_edit(request, pk):
    test = get_object_or_404(Test, pk=pk)
    if request.method == 'POST':
        form = Test(request.POST, instance=test)
        if form.is_valid():
            form.save()
            return redirect(reverse('core:test_detail', kwargs={'pk': test.pk}))
    else:
        form = Test(instance=test)
    return render(request, 'core/test_form.html', {'form': form, 'action': 'Edit', 'test': test})

def test_detail(request, pk):
    test = get_object_or_404(Test, pk=pk)
    return render(request, 'core/test_detail.html', {'test': test})
def test_delete(request, pk):
    test = get_object_or_404(Test, pk=pk)
    if request.method == 'POST':
        test.delete()
        return redirect('core:test_list')


    return render(request, 'core/test_confirm_delete.html', {'test': test})
# PatientTests (results)
def patienttest_list(request):
    patienttest = PatientTest.objects.select_related('patient', 'test')
    return render(request, 'core/patienttest_list.html', {
        'patienttest': patienttest
    })

def patienttest_detail(request, pk):
    patienttest = get_object_or_404(PatientTest, pk=pk)
    return render(
        request,
        'patienttest_detail.html',
        {'patienttest': patienttest }
    )

def patienttest_create(request):
    if request.method == 'POST':
        form = PatientTestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('core:patienttest_list')
    else:
        form = PatientTestForm()

    return render(request, 'core/patienttest_form.html', {
        'form': form
    })

def patienttest_delete(request, pk):
    patienttest = get_object_or_404(PatientTest, pk=pk)

    if request.method == 'POST':
        patienttest.delete()
        return redirect('core:patienttest_list')

    return render(request, 'core/patienttest_confirm_delete.html', {
        'patienttest': patienttest
    })


from .models import PatientTest, TestResult
from .forms import TestResultForm
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import TestResult

@login_required
def testresult_list(request):
    results = TestResult.objects.all()

    user = request.user

    # Doctor
    if user.groups.filter(name='Doctor').exists():
        results = results.filter(status__in=['completed', 'approved'])

    # Lab Staff
    elif user.groups.filter(name='Lab').exists():
        results = results.filter(status__in=['pending', 'completed'])

    # Admin يشوف الكل (ما نفلتر شي)

    context = {
        'result': results
    }
    return render(request, 'core/testresult_list.html', context)
from django.core.paginator import Paginator
def testresult_list(request):
    results = TestResult.objects.all().order_by('-id')
    results = TestResult.objects.select_related(
        'patienttest',
        'patienttest__patient',
        'patienttest__test'
    )

    status = request.GET.get('status')
    search = request.GET.get('search')
    paginator = Paginator(results, 5)  # 5 نتائج بكل صفحة
    page_number = request.GET.get('page')
    page_obj= paginator.get_page(page_number)

    if status:
        results = results.filter(status=status)

    if search:
        results = results.filter(
            patienttest__patient__first_name__icontains=search
        )
        

    context = {
        'result': page_obj,
        'result': results,
        'status': status,
        'search': search,
    }
    return render(request, 'core/testresult_list.html', context)


def testresult_create(request, pk):
    patienttest = get_object_or_404(PatientTest, id=pk)

    if hasattr(patienttest, 'testresult'):
        return redirect('core:testresult_detail', patienttest.testresult.id)

    if request.method == 'POST':
        form = TestResultForm(request.POST)
        if form.is_valid():
            result = form.save(commit=False)
            result.patienttest = patienttest
            result.save()
            patienttest.status = 'completed'
            patienttest.save()

            return redirect('core:testresult_detail', result.id)
    else:
        form = TestResultForm()

    return render(request, 'core/testresult_create.html', {
        'form': form,
        'patienttest': patienttest
    })

def testresult_delete(request, pk):
    result = get_object_or_404(TestResult, id=pk)
    patienttest = result.patienttest

    if request.method == 'POST':
        result.delete()
        return redirect('core:patienttest_detail', patienttest)

    return render(request, 'core/testresult_confirm_delete.html', {
        'result': result
    }) 
from django.shortcuts import render, get_object_or_404
from .models import TestResult

def testresult_detail(request, pk):
    result = get_object_or_404(TestResult, pk=pk)
    return render(request, 'core/testresult_detail.html', {
        'result': result
    })
from .models import PatientTest, TestResult
def testresult_delete(request, pk):
    if not request.user.has_perm('core.delete_testresult'):
     return HttpResponseForbidden()

    result = get_object_or_404(TestResult, pk=pk)

    if result.status == 'approved':
        messages.error(request, "Approved results cannot be deleted.")
        return redirect('core:testresult_detail', pk=pk)

    result.delete()
    messages.success(request, "Result deleted.")
    return redirect('core:testresult_list')
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import TestResult, ActivityLog
from .forms import TestResultForm

@login_required
@permission_required('core.change_testresult', raise_exception=True)
def testresult_update(request, pk):

    result = get_object_or_404(TestResult, pk=pk)

    # 🔒 منع التعديل إذا Approved
    if result.status == 'approved':
        messages.error(request, "Approved results cannot be edited.")
        return redirect('core:testresult_detail', pk=pk)

    if request.method == 'POST':
        form = TestResultForm(request.POST, instance=result)
        if form.is_valid():
            form.save()

            ActivityLog.objects.create(
                user=request.user,
                action=f"Updated result for {result.patienttest.patient}"
            )

            messages.success(request, "Result updated successfully.")
            return redirect('core:testresult_detail', pk=pk)
    else:
        form = TestResultForm(instance=result)

    return render(request, 'core/testresult_form.html', {'form': form})

from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils import timezone
@login_required
@permission_required('core.approve_testresult', raise_exception=True)
@user_passes_test(is_doctor)
def testresult_approve(request, pk):
    result = get_object_or_404(TestResult, pk=pk)

    if result.status == 'completed':
        result.status = 'approved'
        result.approved_by = request.user
        
        result.save()

    return redirect('core:testresult_list')
def testresult_complete(request, pk):
    if not request.user.has_perm('core.change_testresult'):
     return HttpResponseForbidden()

    result = get_object_or_404(TestResult, pk=pk)

    if result.status != 'pending':
        return redirect('core:testresult_detail', pk=pk)

    result.status = 'completed'
    result.save()
    ActivityLog.objects.create(
    user=request.user,
    action=f"Approved result for {result.patienttest.patient}"
)

    messages.success(request, "Result marked as completed.")
    return redirect('core:testresult_detail', pk=pk)

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

def testresult_complete(request, pk):
    result = get_object_or_404(TestResult, pk=pk)

    if result.status == 'pending':
        result.status = 'completed'
        result.completed_by = request.user
        result.completed_at = timezone.now()
        result.save()
        ActivityLog.objects.create(
        user=request.user,
        action=f"Approved result for {result.patienttest.patient}"
)

    return redirect('core:testresult_detail', pk=result.pk)

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import TestResult, Patient, Test

@login_required
def dashboard(request):
    pending_count = TestResult.objects.filter(status='pending').count()
    completed_count = TestResult.objects.filter(status='completed').count()
    approved_count = TestResult.objects.filter(status='approved').count()
    total_results = TestResult.objects.count()

    latest_results = TestResult.objects.select_related(
        'patienttest',
        'patienttest__patient',
        'patienttest__test'
    ).order_by('-id')[:5]

    context = {
        'pending_count': pending_count,
        'completed_count': completed_count,
        'approved_count': approved_count,
        'total_results': total_results,
        'latest_results': latest_results,
    }

    return render(request, 'core/dashboard.html', context)

def testresult_print(request, pk):
    result = get_object_or_404(TestResult, pk=pk)

    if result.status != 'approved':
        messages.error(request, "Only approved results can be printed.")
        return redirect('core:testresult_detail', pk=pk)

    return render(request, 'core/testresult_print.html', {
        'result': result
    })

from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from .models import TestResult, ActivityLog

@login_required
@permission_required('core.approve_testresult', raise_exception=True) # تأكد من اسم الصلاحية
@user_passes_test(is_doctor) # لضمان أن الدكتور فقط هو من يوافق
def testresult_approve(request, pk):
    result = get_object_or_404(TestResult, pk=pk)

    # 🔒 التحقق من الحالة (تأكدنا أنها completed مع حرف d)
    if result.status != 'completed':
        result.status = 'approved'
        result.approved_by = request.user
        result.approved_at = timezone.now()
        result.save()
        messages.error(request, "Only completed results can be approved.")
        return redirect('core:testresult_detail', pk=pk)


    # 📝 تسجيل النشاط
    ActivityLog.objects.create(
        user=request.user,
        action=f"Approved result for {result.patienttest.patient}"
    )

    messages.success(request, f"تمت الموافقة على نتيجة المريض {result.patienttest.patient} بنجاح.")
    
    # الأفضل التوجيه لداشبورد الدكتور بعد الموافقة بدلاً من صفحة التفاصيل
    return redirect('core:doctor_dashboard')


from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

class UserLoginView(LoginView):
    template_name = 'core/login.html'

    def get_success_url(self):
        return reverse_lazy('core:redirect_dashboard')
    
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView


class UserLoginView(LoginView):
    template_name = 'core/role_login.html'


@login_required
def redirect_dashboard(request):

    user = request.user

    if user.groups.filter(name='Reception').exists():
        return redirect('core:reception_dashboard')

    elif user.groups.filter(name='Laboratory').exists():
        return redirect('core:lab_dashboard')

    elif user.groups.filter(name='Accounting').exists():
        return redirect('core:accounting_dashboard')

    elif user.is_superuser:
        return redirect('/admin/')

    return redirect('core:login')


@login_required
def reception_dashboard(request):
    return render(request, 'core/reception_dashboard.html')


@login_required
def lab_dashboard(request):
    return render(request, 'core/lab_dashboard.html')


@login_required
def accounting_dashboard(request):
    return render(request, 'core/accounting_dashboard.html')

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required


def home(request):
    return render(request, 'core/home.html')

def login(request, role):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # مدير
            if role == 'manager' and user.is_superuser:
                return redirect('core:manager_dashboard')

            # دكتور
            elif role == 'doctor':
                return redirect('core:doctor_dashboard')

            # حسابات
            elif role == 'accounting':
                return redirect('core:accounting_dashboard')

            # مختبر
            elif role == 'lab':
                return redirect('core:lab_dashboard')

            else:
                return render(request, 'core/role_login.html', {
                    'error': 'ليس لديك صلاحية لهذا القسم',
                    'role': role
                })

        return render(request, 'core/role_login.html', {
            'error': 'اسم المستخدم او كلمة المرور غير صحيحة',
            'role': role
        })

    return render(request, 'core/role_login.html', {'role': role})

from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncMonth
from django.db.models import Count
from .models import Patient
from .models import TestResult
@login_required
def doctor_dashboard(request):
    # تم التصحيح إلى completed ليتطابق مع حالة النظام
    completed_results = TestResult.objects.filter(status='completed')

    context = {
        'completed_results': completed_results
    }
    return render(request, 'core/doctor_dashboard.html', context)

@login_required
def manager_dashboard(request):
    pending_count = TestResult.objects.filter(status='pending').count()
    # تم التصحيح هنا أيضاً
    complete_count = TestResult.objects.filter(status='completed').count()
    approved_count = TestResult.objects.filter(status='approved').count()

    context = {
        'patients_count': Patient.objects.count(),
        'tests_count': Test.objects.count(),
        'results_count': TestResult.objects.count(),
        'pending_count': pending_count,
        'complete_count': complete_count,
        'approved_count': approved_count,
    }

    # الجزء الخاص بالرسم البياني (Revenue)
    monthly_revenue = TestResult.objects.filter(status='approved') \
    .annotate(month=TruncMonth('approved_at')) \
    .values('month') \
    .annotate(total=Sum('patienttest__test__price')) \
    .order_by('month')

    months = [entry['month'].strftime('%b %Y') for entry in monthly_revenue if entry['month']]
    totals = [float(entry['total'] or 0) for entry in monthly_revenue]

    context['months'] = json.dumps(months)
    context['totals'] = json.dumps(totals)
    return render(request, 'core/manager_dashboard.html', context)

@login_required
def lab_dashboard(request):

    pending_results = TestResult.objects.filter(status='pending')
    orders = LabOrder.objects.all()
    context = {
        'pending_results': pending_results,
        'orders' : orders
    }

    return render(request, 'core/lab_dashboard.html', context)

from django.db.models import Sum
from django.utils.timezone import now
from datetime import datetime

@login_required
def accounting_dashboard(request):

    approved_results = TestResult.objects.filter(status='approved')

    filter_type = request.GET.get('filter')

    if filter_type == 'daily':
        today = now().date()
        approved_results = approved_results.filter(created_at__date=today)

    elif filter_type == 'monthly':
        today = now()
        approved_results = approved_results.filter(
            created_at__year=today.year,
            created_at__month=today.month
        )

    total_revenue = approved_results.aggregate(
        total=Sum('patienttest__test__price')
    )['total'] or 0

    context = {
        'approved_results': approved_results,
        'total_revenue': total_revenue
    }

    return render(request, 'core/accounting_dashboard.html', context)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table
from reportlab.platypus import TableStyle
from django.http import HttpResponse

def testresult_pdf(request, pk):

    result = TestResult.objects.get(pk=pk)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="result_{pk}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    data = [
        ["Patient Name", result.patienttest.patient_name],
        ["Test Name", result.patienttest.test_name],
        ["Result", result.result_valu],
        ["Status", result.status],
    ]

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))

    doc.build(elements)

    return response

from openpyxl import Workbook
from django.http import HttpResponse
from django.db.models import Sum

@login_required
def export_manager_report(request):

    wb = Workbook()
    ws = wb.active
    ws.title = "Manager Report"

    # Counts
    patients_count = Patient.objects.count()
    tests_count = Test.objects.count()
    results_count = TestResult.objects.count()
    pending_count = TestResult.objects.filter(status='pending').count()
    complete_count = TestResult.objects.filter(status='complete').count()
    approved_count = TestResult.objects.filter(status='approved').count()

    total_revenue = TestResult.objects.filter(status='approved').aggregate(
        total=Sum('patienttest__test__price')
    )['total'] or 0

    # Write data
    ws.append(["Metric", "Value"])
    ws.append(["Total Patients", patients_count])
    ws.append(["Total Tests", tests_count])
    ws.append(["Total Results", results_count])
    ws.append(["Pending Results", pending_count])
    ws.append(["Completed Results", complete_count])
    ws.append(["Approved Results", approved_count])
    ws.append(["Total Revenue", total_revenue])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=manager_report.xlsx"

    wb.save(response)
    return response

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable
from django.http import HttpResponse
from datetime import datetime
import io

def export_manager_pdf(request):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []

    styles = getSampleStyleSheet()

    # Custom Title Style
    title_style = styles["Heading1"]
    subtitle_style = styles["Normal"]

    # جلب البيانات
    from .models import Patient, Test, TestResult

    patients_count = Patient.objects.count()
    tests_count = Test.objects.count()
    results_count = TestResult.objects.count()

    pending = TestResult.objects.filter(status='pending').count()
    completed = TestResult.objects.filter(status='completed').count()
    approved = TestResult.objects.filter(status='approved').count()

    # ===== HEADER =====
    elements.append(Paragraph("LIMS - Laboratory Information System", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Manager Dashboard Official Report", subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 0.4 * inch))

    # ===== TABLE DATA =====
    data = [
        ["Metric", "Value"],
        ["Total Patients", patients_count],
        ["Total Tests", tests_count],
        ["Total Results", results_count],
        ["Pending Results", pending],
        ["Completed Results", completed],
        ["Approved Results", approved],
    ]

    table = Table(data, colWidths=[270, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))

    # ===== FOOTER =====
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(
        Paragraph(
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | © 2026 LIMS",
            styles["Normal"]
        )
    )

    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

def add_result(request, order_id):

    order = LabOrder.objects.get(id=order_id)

    if request.method == "POST":

        value = request.POST.get("value")

        ParameterResult.objects.create(
            lab_order=order,
            value=value
        )

    return render(request, "core/add_result.html", {"order": order})

def landing(request):
    return render(request, 'core/landing.html')