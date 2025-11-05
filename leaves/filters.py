import django_filters
from .models import Holiday, LeaveRequest, LeaveTracker
from django.db.models import F

class HolidayCustomFilter(django_filters.FilterSet):
    after = django_filters.DateFilter(field_name='date', lookup_expr='gte')

    class Meta:
        model = Holiday
        fields = ['name']

class LeaveRequestCustomFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    date_upto = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    days_gt = django_filters.NumberFilter(field_name='days', lookup_expr='gte')

    class Meta:
        model = LeaveRequest
        fields = ['status']

class TeamLeaveTrackerCustomFilter(django_filters.FilterSet):
    leaves_taken_gt = django_filters.NumberFilter(field_name='leaves_taken', lookup_expr='gte')
    leaves_left_lt = django_filters.NumberFilter(method='leaves_left')

    def leaves_left(self, queryset, name, value):
        # breakpoint()
        query = queryset.annotate(leaves_left=F('total_leaves') - F('leaves_taken'))
        return query.filter(leaves_left__lte = value)

    class Meta:
        model = LeaveTracker
        fields = ['leaves_taken']