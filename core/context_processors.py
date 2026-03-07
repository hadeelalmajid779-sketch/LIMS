from .models import TestResult

def global_counts(request):

    return {
        'pending_count': TestResult.objects.filter(status='pending').count(),
        'complete_count': TestResult.objects.filter(status='complete').count(),
        'approved_count': TestResult.objects.filter(status='approved').count(),
    }