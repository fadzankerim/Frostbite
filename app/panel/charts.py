"""Vremenske serije za analitiku (crta ih frontend, ColumnChart)."""
from datetime import timedelta


def daily_series(qs, field, days, today):
    """Broj zapisa po danu za posljednjih `days` dana (uključujući danas)."""
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    start = today - timedelta(days=days - 1)
    counts = dict(qs.filter(**{f'{field}__date__gte': start}).annotate(d=TruncDate(field))
                  .values('d').annotate(c=Count('id')).values_list('d', 'c'))
    return [(f'{(start + timedelta(days=i)).day}.{(start + timedelta(days=i)).month}.',
             counts.get(start + timedelta(days=i), 0)) for i in range(days)]


MONTHS = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']


def last_months(today, n):
    """Lista (godina, mjesec) za posljednjih n mjeseci, od najstarijeg."""
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))
