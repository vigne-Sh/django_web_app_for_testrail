from django.db.models import Count, Max
from .models import testrail_db


def check_distinct():
    unique_fields = ['testrail_name', 'Date', 'total', 'manager', 'user_id']

    duplicates = (
        testrail_db.objects.values(*unique_fields)
        .order_by()
        .annotate(max_id=Max('id'), count_id=Count('id'))
        .filter(count_id__gt=1)
    )

    for duplicate in duplicates:
        (
            testrail_db.objects
            .filter(**{x: duplicate[x] for x in unique_fields})
            .exclude(id=duplicate['max_id'])
            .delete()
        )