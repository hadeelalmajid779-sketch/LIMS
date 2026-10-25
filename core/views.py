"""
Cleaned views for the LIMS Django application.

This file keeps the view names used by core/urls.py and removes duplicate
definitions. It is designed against the models.py and forms.py provided.
Before replacing the live file, run the checks listed in the accompanying
instructions and test the pages in a development environment.
"""
import io
import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timezone import now

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .forms import PatientForm, PatientTestForm, TestForm, TestResultForm
from .models import (
    ActivityLog,
    LabOrder,
    ParameterResult,
    Patient,
    PatientTest,
    Test,
    TestParameter,
    TestResult,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def is_doctor(user):
    return user.is_authenticated and user.groups.filter(name="Doctor").exists()


def is_lab_staff(user):
    return user.is_authenticated and (
        user.groups.filter(name="Laboratory").exists()
        or user.groups.filter(name="Lab").exists()
    )


def _record_activity(user, action):
    """Write an audit entry without blocking the main action if user is anonymous."""
    if user and user.is_authenticated:
        ActivityLog.objects.create(user=user, action=action)


def pending_results_count(request):
    if request.user.is_authenticated:
        return {
            "pending_results_count": TestResult.objects.filter(status="pending").count()
        }
    return {}


# ---------------------------------------------------------------------------
# Landing, home and authentication
# ---------------------------------------------------------------------------

def landing(request):
    return render(request, "core/landing.html")


def home(request):
    return render(request, "core/home.html")


class UserLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("core:redirect_dashboard")


def role_login(request, role):
    """
    Role-specific login endpoint used by urls.py:role_login/<role>/.
    Authenticated users must belong to the requested role (or be a superuser
    for the manager section).
    """
    role_group_names = {
        "manager": ("Manager",),
        "doctor": ("Doctor",),
        "accounting": ("Accounting",),
        "lab": ("Laboratory", "Lab"),
    }

    if role not in role_group_names:
        return render(
            request,
            "core/role_login.html",
            {"role": role, "roletitle": role.title(), "error": "The section is not recognized."},
            status=404,
        )

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(
                request,
                "core/role_login.html",
                {
                    "role": role,
                    "roletitle": role.title(),
                    "error": "Invalid username or password.",
                },
            )

        allowed = user.is_superuser if role == "manager" else user.groups.filter(
            name__in=role_group_names[role]
        ).exists()

        if not allowed:
            return render(
                request,
                "core/role_login.html",
                {
                    "role": role,
                    "roletitle": role.title(),
                    "error": "You do not have permission to access this section.",
                },
                status=403,
            )

        # Importing Django's login function under an alias avoids shadowing
        # this view function, which is also named login.
        from django.contrib.auth import login as auth_login
        auth_login(request, user)

        destinations = {
            "manager": "core:manager_dashboard",
            "doctor": "core:doctor_dashboard",
            "accounting": "core:accounting_dashboard",
            "lab": "core:lab_dashboard",
        }
        return redirect(destinations[role])

    return render(
        request,
        "core/role_login.html",
        {"role": role, "roletitle": role.title()},
    )

@login_required
def redirect_dashboard(request):
    user = request.user

    if user.is_superuser:
        return redirect("/admin/")
    if user.groups.filter(name="Reception").exists():
        return redirect("core:reception_dashboard")
    if user.groups.filter(name="Laboratory").exists():
        return redirect("core:lab_dashboard")
    if user.groups.filter(name="Accounting").exists():
        return redirect("core:accounting_dashboard")
    if user.groups.filter(name="Doctor").exists():
        return redirect("core:doctor_dashboard")
    if user.groups.filter(name="Manager").exists():
        return redirect("core:manager_dashboard")

    return redirect("core:dashboard")



# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------
@login_required
def patient_list(request):
    patients = Patient.objects.all()
    return render(
        request,
        "core/patient_list.html",
        {"patients": patients}
    )


@login_required
def patient_create(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            if not patient.test_subject_id:
                patient.test_subject_id = f"LIMS-{uuid4().hex[:8].upper()}"
            patient.save()
            _record_activity(request.user, f"Registered patient {patient.test_subject_id}")
            messages.success(request, "Patient registered successfully.")
            return redirect("core:patient_detail", pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, "core/patient_form.html", {"form": form})


@login_required
def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            _record_activity(request.user, f"Updated patient {patient.test_subject_id}")
            messages.success(request, "Patient record updated successfully.")
            return redirect("core:patient_detail", pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, "core/patient_form.html", {"form": form, "patient": patient})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient_tests = PatientTest.objects.filter(patient=patient).select_related("test")
    return render(
        request,
        "core/patient_detail.html",
        {"patient": patient, "patienttest": patient_tests, "patient_tests": patient_tests},
    )


@login_required
def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        patient_id = patient.test_subject_id
        patient.delete()
        _record_activity(request.user, f"Deleted patient {patient_id}")
        messages.success(request, "Patient record deleted successfully.")
        return redirect("core:patient_list")
    return render(request, "core/patient_confirm_delete.html", {"patient": patient})


# ---------------------------------------------------------------------------
# Test catalogue
# ---------------------------------------------------------------------------

@login_required
def test_list(request):
    tests = Test.objects.all().order_by("department", "test_name")
    return render(request, "core/test_list.html", {"test": tests, "tests": tests})


@login_required
def test_create(request):
    if request.method == "POST":
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save()
            _record_activity(request.user, f"Created test {test.test_code}")
            messages.success(request, "Test created successfully.")
            return redirect("core:test_detail", pk=test.pk)
    else:
        form = TestForm()
    return render(request, "core/test_form.html", {"form": form, "action": "Create"})


@login_required
def test_edit(request, pk):
    test = get_object_or_404(Test, pk=pk)
    if request.method == "POST":
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            _record_activity(request.user, f"Updated test {test.test_code}")
            messages.success(request, "Test updated successfully")
            return redirect("core:test_detail", pk=test.pk)
    else:
        form = TestForm(instance=test)
    return render(
        request, "core/test_form.html", {"form": form, "action": "Edit", "test": test}
    )


@login_required
def test_detail(request, pk):
    test = get_object_or_404(Test, pk=pk)
    return render(request, "core/test_detail.html", {"test": test})


@login_required
def test_delete(request, pk):
    test = get_object_or_404(Test, pk=pk)
    if request.method == "POST":
        code = test.test_code
        try:
            test.delete()
        except Exception:
            messages.error(request,"Unable to delete the test because it is linked to existing records.")
            return redirect("core:test_detail", pk=pk)
        _record_activity(request.user, f"Deleted test {code}")
        messages.success(request, "Test deleted successfully.")
        return redirect("core:test_list")
    return render(request, "core/test_confirm_delete.html", {"test": test})


# ---------------------------------------------------------------------------
# Patient test requests
# ---------------------------------------------------------------------------
@login_required
def patienttest_list(request):
    patienttest_list = PatientTest.objects.select_related(
        "patient", "test"
    )
    return render(
        request,
        "core/patienttest_list.html",
        {"patienttest_list": patienttest_list},
    )

@login_required
def patienttest_detail(request, pk):
    patient_test = get_object_or_404(
        PatientTest.objects.select_related("patient", "test"), pk=pk
    )
    result = TestResult.objects.filter(patienttest=patient_test).first()
    return render(
        request,
        "core/patienttest_detail.html",
        {"patienttest": patient_test, "result": result},
    )


@login_required
def patienttest_create(request):
    if request.method == "POST":
        form = PatientTestForm(request.POST)
        if form.is_valid():
            patient_test = form.save()
            _record_activity(
                request.user,
                f"Created test request {patient_test.pk} for {patient_test.patient}",
            )
            messages.success(request, "Test order registered successfully.")
            return redirect("core:patienttest_list")
    else:
        form = PatientTestForm()
    return render(request, "core/patienttest_form.html", {"form": form})


@login_required
def patienttest_delete(request, pk):
    patient_test = get_object_or_404(PatientTest, pk=pk)
    if request.method == "POST":
        patient_test_id = patient_test.pk
        patient_test.delete()
        _record_activity(request.user, f"Deleted patient test request {patient_test_id}")
        messages.success(request, "Test request deleted successfully.")
        return redirect("core:patienttest_list")
    return render(
        request,
        "core/patienttest_confirm_delete.html",
        {"patienttest": patient_test},
    )


# ---------------------------------------------------------------------------
# Test results
# ---------------------------------------------------------------------------

@login_required
def testresult_list(request):
    results = TestResult.objects.select_related(
        "patienttest", "patienttest__patient", "patienttest__test"
    ).order_by("-id")

    user = request.user
    if user.groups.filter(name="Doctor").exists():
        results = results.filter(status__in=["completed", "approved"])
    elif user.groups.filter(name__in=["Lab", "Laboratory"]).exists():
        results = results.filter(status__in=["pending", "completed"])

    status = request.GET.get("status", "").strip()
    search = request.GET.get("search", "").strip()

    if status in {"pending", "completed", "approved"}:
        results = results.filter(status=status)
    if search:
        results = results.filter(
            patienttest__patient__first_name__icontains=search
        ) | results.filter(
            patienttest__patient__last_name__icontains=search
        ) | results.filter(
            patienttest__patient__test_subject_id__icontains=search
        )

    paginator = Paginator(results.distinct(), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/testresult_list.html",
        {
            "result": page_obj,
            "results": page_obj,
            "status": status,
            "search": search,
            "page_obj": page_obj,
        },
    )


@login_required
def testresult_create(request, pk):
    patient_test = get_object_or_404(
        PatientTest.objects.select_related("patient", "test"), pk=pk
    )
    existing_result = TestResult.objects.filter(patienttest=patient_test).first()
    if existing_result:
        return redirect("core:testresult_detail", pk=existing_result.pk)

    if request.method == "POST":
        form = TestResultForm(request.POST)
        if form.is_valid():
            result = form.save(commit=False)
            result.patienttest = patient_test
            result.save()
            patient_test.status = "completed"
            result.save()
            _record_activity(
                request.user, f"Created result {result.pk} for {patient_test.patient}"
            )
            messages.success(request, "Test result saved successfully.")
            return redirect("core:testresult_detail", pk=result.pk)
    else:
        form = TestResultForm(
            initial={
                "unit": patient_test.test.unit or "",
                "reference_range": patient_test.test.reference_range or "",
            }
        )

    return render(
        request,
        "core/testresult_create.html",
        {"form": form, "patienttest": patient_test},
    )


@login_required
def testresult_detail(request, pk):
    result = get_object_or_404(
        TestResult.objects.select_related(
            "patienttest", "patienttest__patient", "patienttest__test"
        ),
        pk=pk,
    )
    return render(request, "core/testresult_detail.html", {"result": result})


@login_required
@permission_required("core.change_testresult", raise_exception=True)
def testresult_update(request, pk):
    result = get_object_or_404(TestResult, pk=pk)
    if result.status == "approved":
        messages.error(request, "You cannot edit a result that has been approved.")
        return redirect("core:testresult_detail", pk=pk)

    if request.method == "POST":
        form = TestResultForm(request.POST, instance=result)
        if form.is_valid():
            form.save()
            _record_activity(
                request.user, f"Updated result {result.pk} for {result.patienttest.patient}"
            )
            messages.success(request, "Test result updated successfully.")
            return redirect("core:testresult_detail", pk=pk)
    else:
        form = TestResultForm(instance=result)
    return render(request, "core/testresult_form.html", {"form": form, "result": result})


@login_required
@permission_required("core.change_testresult", raise_exception=True)
def testresult_complete(request, pk):
    result = get_object_or_404(TestResult, pk=pk)
    if request.method != "POST":
        return redirect("core:testresult_detail", pk=pk)
    if result.status != "pending":
        messages.info(request, "The result status is not pending.")
        return redirect("core:testresult_detail", pk=pk)

    result.status = "completed"
    result.completed_by = request.user
    result.completed_at = timezone.now()
    result.save()
    result.patienttest.status = "completed"
    result.patienttest.save()
    _record_activity(request.user, f"Marked result {result.pk} completed")
    messages.success(request, "Result marked as completed.")
    return redirect("core:testresult_detail", pk=pk)


@login_required
@permission_required("core.approve_testresult", raise_exception=True)
@user_passes_test(is_doctor)
def testresult_approve(request, pk):
    result = get_object_or_404(TestResult, pk=pk)
    if request.method != "POST":
        return redirect("core:testresult_detail", pk=pk)
    if result.status != "completed":
        messages.error(request, "Cannot approve the result before it is completed.")
        return redirect("core:testresult_detail", pk=pk)

    result.status = "approved"
    result.approved_by = request.user
    result.approved_at = timezone.now()
    result.save()
    _record_activity(request.user, f"Approved result {result.pk}")
    messages.success(request, "Test result approved successfully.")
    return redirect("core:testresult_detail", pk=pk)


@login_required
@permission_required("core.delete_testresult", raise_exception=True)
def testresult_delete(request, pk):
    result = get_object_or_404(TestResult, pk=pk)
    if result.status == "approved":
        messages.error(request, "You cannot delete an approved result.")
        return redirect("core:testresult_detail", pk=pk)
    if request.method == "POST":
        result_id = result.pk
        result.delete()
        _record_activity(request.user, f"Deleted result {result_id}")
        messages.success(request, "Test result deleted successfully.")
        return redirect("core:testresult_list")
    return render(request, "core/testresult_confirm_delete.html", {"result": result})


@login_required
def testresult_print(request, pk):
    result = get_object_or_404(
        TestResult.objects.select_related(
            "patienttest", "patienttest__patient", "patienttest__test"
        ),
        pk=pk,
    )
    if result.status != "approved":
        messages.error(request, "You cannot print the report before the result is approved.")
        return redirect("core:testresult_detail", pk=pk)
    return render(request, "core/testresult_print.html", {"result": result})


@login_required
def testresult_pdf(request, pk):
    result = get_object_or_404(
        TestResult.objects.select_related(
            "patienttest", "patienttest__patient", "patienttest__test"
        ),
        pk=pk,
    )
    if result.status != "approved":
        messages.error(request, "You cannot generate the report before the result is approved.")
        return redirect("core:testresult_detail", pk=pk)

    patient = result.patienttest.patient
    test = result.patienttest.test
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="result_{pk}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("LIMS - Laboratory Test Result", styles["Title"]),
        Spacer(1, 0.25 * inch),
        Paragraph(f"Patient: {patient.first_name} {patient.middle or ''} {patient.last_name}", styles["Normal"]),
        Paragraph(f"Patient ID: {patient.test_subject_id}", styles["Normal"]),
        Paragraph(f"Test: {test.test_name} ({test.test_code})", styles["Normal"]),
        Spacer(1, 0.2 * inch),
    ]
    data = [
        ["Field", "Value"],
        ["Result", result.result_value or ""],
        ["Unit", result.unit or test.unit or ""],
        ["Reference range", result.reference_range or test.reference_range or ""],
        ["WBC", "" if result.wbc is None else str(result.wbc)],
        ["RBC", "" if result.rbc is None else str(result.rbc)],
        ["Hemoglobin", "" if result.hemoglobin is None else str(result.hemoglobin)],
        ["Hematocrit", "" if result.hematocrit is None else str(result.hematocrit)],
        ["Platelets", "" if result.platelets is None else str(result.platelets)],
        ["Status", result.get_status_display()],
        ["Approved at", result.approved_at.strftime("%Y-%m-%d %H:%M") if result.approved_at else ""],
    ]
    table = Table(data, colWidths=[180, 300])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return response


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    context = {
        "pending_count": TestResult.objects.filter(status="pending").count(),
        "completed_count": TestResult.objects.filter(status="completed").count(),
        "approved_count": TestResult.objects.filter(status="approved").count(),
        "total_results": TestResult.objects.count(),
        "latest_results": TestResult.objects.select_related(
            "patienttest", "patienttest__patient", "patienttest__test"
        ).order_by("-id")[:5],
    }
    return render(request, "core/dashboard.html", context)


@login_required
@user_passes_test(
    lambda user: user.is_authenticated
    and user.groups.filter(name="Reception").exists()
)
def reception_dashboard(request):
    return render(request, "core/reception_dashboard.html")

@login_required
@user_passes_test(is_lab_staff)
def lab_dashboard(request):
    pending_results = TestResult.objects.filter(status="pending").select_related(
        "patienttest", "patienttest__patient", "patienttest__test"
    )
    orders = LabOrder.objects.select_related("patient", "test").order_by("-created_at")
    return render(
        request,
        "core/lab_dashboard.html",
        {"pending_results": pending_results, "orders": orders},
    )



@login_required
@user_passes_test(is_doctor)
def doctor_dashboard(request):
    completed_results = TestResult.objects.filter(
        status="completed"
    ).select_related("patienttest", "patienttest__patient", "patienttest__test")
    return render(
        request,
        "core/doctor_dashboard.html",
        {"completed_results": completed_results},
    )


@login_required
def manager_dashboard(request):
    context = {
        "patients_count": Patient.objects.count(),
        "tests_count": Test.objects.count(),
        "results_count": TestResult.objects.count(),
        "pending_count": TestResult.objects.filter(status="pending").count(),
        "complete_count": TestResult.objects.filter(status="completed").count(),
        "approved_count": TestResult.objects.filter(status="approved").count(),
    }

    # عدد المرضى المسجلين شهريًا
    monthly_patients = (
        Patient.objects
        .annotate(month=TruncMonth("registration_date"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    patient_months = [
        entry["month"].strftime("%b %Y")
        for entry in monthly_patients
        if entry["month"] is not None
    ]

    patient_totals = [
        entry["total"]
        for entry in monthly_patients
        if entry["month"] is not None
    ]

    context["labelssafe"] = json.dumps(patient_months)
    context["datasafe"] = json.dumps(patient_totals)

    # الإيرادات الشهرية للنتائج المعتمدة
    monthly_revenue = (
        TestResult.objects
        .filter(status="approved", approved_at__isnull=False)
        .annotate(month=TruncMonth("approved_at"))
        .values("month")
        .annotate(total=Sum("patienttest__total_price"))
        .order_by("month")
    )

    months = [
        entry["month"].strftime("%b %Y")
        for entry in monthly_revenue
        if entry["month"] is not None
    ]

    totals = [
        float(entry["total"] or 0)
        for entry in monthly_revenue
        if entry["month"] is not None
    ]

    context["months"] = json.dumps(months)
    context["totals"] = json.dumps(totals)

    return render(request, "core/manager_dashboard.html", context)


@login_required
@user_passes_test(lambda user: user.is_authenticated and user.groups.filter(name="Accounting").exists())
def accounting_dashboard(request):
    approved_results = TestResult.objects.filter(status="approved").select_related(
        "patienttest", "patienttest__patient", "patienttest__test"
    )
    filter_type = request.GET.get("filter")
    current_time = now()

    if filter_type == "daily":
        approved_results = approved_results.filter(approved_at__date=current_time.date())
    elif filter_type == "monthly":
        approved_results = approved_results.filter(
            approved_at__year=current_time.year, approved_at__month=current_time.month
        )

    total_revenue = approved_results.aggregate(
        total=Sum("patienttest__total_price")
    )["total"] or Decimal("0.00")
    return render(
        request,
        "core/accounting_dashboard.html",
        {"approved_results": approved_results, "total_revenue": total_revenue},
    )


# ---------------------------------------------------------------------------
# Manager reports
# ---------------------------------------------------------------------------

@login_required
def export_manager_report(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Manager Report"

    patients_count = Patient.objects.count()
    tests_count = Test.objects.count()
    results_count = TestResult.objects.count()
    pending_count = TestResult.objects.filter(status="pending").count()
    completed_count = TestResult.objects.filter(status="completed").count()
    approved_results = TestResult.objects.filter(status="approved")
    approved_count = approved_results.count()
    total_revenue = approved_results.aggregate(
        total=Sum("patienttest__total_price")
    )["total"] or Decimal("0.00")

    rows = [
        ["Metric", "Value"],
        ["Total Patients", patients_count],
        ["Total Tests", tests_count],
        ["Total Results", results_count],
        ["Pending Results", pending_count],
        ["Completed Results", completed_count],
        ["Approved Results", approved_count],
        ["Total Revenue", float(total_revenue)],
    ]
    for row in rows:
        worksheet.append(row)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="manager_report.xlsx"'
    workbook.save(response)
    return response


@login_required
def export_manager_pdf(request):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("LIMS - Laboratory Information Management System", styles["Title"]),
        Spacer(1, 0.2 * inch),
        Paragraph("Manager Dashboard Report", styles["Normal"]),
        Spacer(1, 0.2 * inch),
        HRFlowable(width="100%", thickness=1, color=colors.grey),
        Spacer(1, 0.3 * inch),
    ]

    approved_results = TestResult.objects.filter(status="approved")
    total_revenue = approved_results.aggregate(
        total=Sum("patienttest__total_price")
    )["total"] or Decimal("0.00")
    data = [
        ["Metric", "Value"],
        ["Total Patients", Patient.objects.count()],
        ["Total Tests", Test.objects.count()],
        ["Total Results", TestResult.objects.count()],
        ["Pending Results", TestResult.objects.filter(status="pending").count()],
        ["Completed Results", TestResult.objects.filter(status="completed").count()],
        ["Approved Results", approved_results.count()],
        ["Total Revenue", f"{total_revenue:.2f}"],
    ]
    table = Table(data, colWidths=[270, 150])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]
        )
    )
    elements.extend(
        [
            table,
            Spacer(1, 0.4 * inch),
            HRFlowable(width="100%", thickness=1, color=colors.grey),
            Spacer(1, 0.15 * inch),
            Paragraph(
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles["Normal"],
            ),
        ]
    )
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="manager_report.pdf"'
    return response


# ---------------------------------------------------------------------------
# Parameter-based laboratory orders (separate from PatientTest/TestResult)
# ---------------------------------------------------------------------------

@login_required
def add_result(request, order_id):
    order = get_object_or_404(
        LabOrder.objects.select_related("patient", "test"), pk=order_id
    )
    parameters = TestParameter.objects.filter(test=order.test)

    if request.method == "POST":
        parameter_id = request.POST.get("parameter")
        value_text = request.POST.get("value", "").strip()
        parameter = get_object_or_404(parameters, pk=parameter_id)

        try:
            value = float(value_text)
        except (TypeError, ValueError):
            messages.error(request,"Please enter a valid numeric value.")
        else:
            ParameterResult.objects.update_or_create(
                order=order,
                parameter=parameter,
                defaults={"value": value},
            )
            if order.status == "pending":
                order.status = "in_progress"
                order.save(update_fields=["status"])
            _record_activity(
                request.user, f"Recorded parameter {parameter.name} for lab order {order.pk}"
            )
            messages.success(request, "Test result saved successfully.")
            return redirect("core:lab_dashboard")

    return render(
        request,
        "core/add_result.html",
        {"order": order, "parameters": parameters, "results": order.results.select_related("parameter")},
    )
