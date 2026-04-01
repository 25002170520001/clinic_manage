from datetime import datetime, time, timedelta

from django.utils import timezone


def local_day_window():
    day = timezone.localdate()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    end = start + timedelta(days=1)
    return start, end


def filter_today(queryset, field_name="created_at"):
    start, end = local_day_window()
    return queryset.filter(**{f"{field_name}__gte": start, f"{field_name}__lt": end})
