from django.contrib import admin
from .models import ( Patient,Test,PatientTest,TestParameter,LabOrder,ParameterResult)


# =========================
# Test Parameter Inline
# =========================
class TestParameterInline(admin.TabularInline):
    model = TestParameter
    extra = 1
class ParameterResultInline(admin.TabularInline):
    model = ParameterResult
    extra = 0
    readonly_fields = ('flag',)


# =========================
# Patient Admin
# =========================
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('test_subject_id', 'first_name', 'last_name', 'gender', 'phone', 'registration_date')
    search_fields = ('test_subject_id', 'national_id', 'first_name', 'last_name', 'phone')
    readonly_fields = ('registration_date', 'last_update')
    fieldsets = (
        ('Identity', {
            'fields': ('test_subject_id', 'national_id', 'first_name',
                       'last_name', 'date_of_birth', 'gender', 'blood_group')
        }),
        ('Contact & Notes', {
            'fields': ('phone', 'email', 'address', 'emergency_contact', 'notes')
        }),
        ('Administration', {
            'fields': ('registration_date', 'last_update')
        }),
    )


# =========================
# Test Admin (WITH PARAMETERS INLINE)
# =========================
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('test_code', 'test_name', 'department', 'price', 'active')
    search_fields = ('test_code', 'test_name', 'department')
    list_filter = ('department', 'active')
    readonly_fields = ('created_at', 'last_update')
    inlines = [TestParameterInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('test_code', 'test_name', 'department',
                       'sample_type', 'unit', 'reference_range')
        }),
        ('Pricing & Time', {
            'fields': ('price', 'turnaround_time_hours', 'active')
        }),
    )


# =========================
# Lab Order Admin
# =========================
from django.utils.html import format_html
from django.contrib import messages

@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ('patient', 'test', 'status', 'created_at')
    inlines = [ParameterResultInline]
    actions = ['approve_orders']

    def approve_orders(self, request, queryset):
        for order in queryset:
            try:
                order.approve()
                self.message_user(request, "Order approved successfully.")
            except Exception as e:
                self.message_user(request, str(e), level=messages.ERROR)

    approve_orders.short_description = "Approve selected orders"
    def get_readonly_fields(self, request, obj = None):
        if obj and obj.status == 'approved':
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)
    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'approved':
            return False
        return super().has_change_permission(request, obj)

# =========================
# Parameter Result Admin
# =========================
from django.utils.html import format_html

@admin.register(ParameterResult)
class ParameterResultAdmin(admin.ModelAdmin):
    list_display = ('order', 'parameter', 'value', 'colored_flag')

    def colored_flag(self, obj):
        if obj.flag == 'High':
            color = 'red'
        elif obj.flag == 'Low':
            color = 'blue'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.flag
        )

    colored_flag.short_description = 'Flag'
# =========================
# PatientTest Admin (القديم)
# =========================
@admin.register(PatientTest)
class PatientTestAdmin(admin.ModelAdmin):
    list_display = ('patient', 'test', 'price_snapshot',
                    'discount_percent', 'total_price',
                    'request_date', 'result_date')
    readonly_fields = ('price_snapshot', 'total_price', 'request_date')

class ParameterResultInline(admin.TabularInline):
    model = ParameterResult
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'approved':
            return False
        return super().has_change_permission(request, obj)

    def has_add_permission(self, request, obj):
        if obj and obj.status == 'approved':
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == 'approved':
            return False
        return super().has_delete_permission(request, obj)