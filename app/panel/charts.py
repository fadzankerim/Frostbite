"""Stubičasti grafikoni kao SVG geometrija izračunata na serveru.

Zašto SVG atributi, a ne CSS visine: CSP ne dozvoljava inline style atribute, a SVG
atributi (x, y, height) nisu stil. Specifikacija oznaka (dataviz): stub najviše 24px,
4px zaobljen vrh, ravan kod osnovice, tanke recesivne linije mreže, zaokružene oznake ose.
"""
import math
from datetime import timedelta

BAR_MAX = 24
RADIUS = 4


def _nice_scale(v):
    """Cijeli, okrugli koraci ose (1, 2, 5 x 10^k), najviše ~5 podioka; vraća (maksimum ose, korak)."""
    if v <= 0:
        return 4, 1
    raw = v / 4
    exp = 10 ** math.floor(math.log10(raw)) if raw >= 1 else 1
    step = next(m * exp for m in (1, 2, 5, 10) if m * exp >= raw)
    return step * math.ceil(v / step), step


def _bar_path(x, y, w, h):
    """Stub sa zaobljenim vrhom (4px) i ravnom osnovicom."""
    if h <= 0:
        return ''
    r = min(RADIUS, w / 2, h)
    return (f'M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
            f'L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} L{x + w:.1f},{y + h:.1f} Z')


def column_chart(items, unit='', width=640, height=220):
    """items: lista (oznaka, vrijednost). Vraća geometriju za predložak panel/_column_chart.html."""
    left, right, top, bottom = 44, 8, 12, 28
    pw, ph = width - left - right, height - top - bottom
    vmax, step = _nice_scale(max((v for _, v in items), default=0))
    n = max(len(items), 1)
    slot = pw / n
    bw = min(BAR_MAX, slot * .62)
    bars = []
    for i, (label, value) in enumerate(items):
        h = ph * (value / vmax) if vmax else 0
        x = left + i * slot + (slot - bw) / 2
        y = top + ph - h
        bars.append({
            'label': label, 'value': value, 'path': _bar_path(x, y, bw, h),
            'hit_x': f'{left + i * slot:.1f}', 'hit_w': f'{slot:.1f}',
            'lx': f'{x + bw / 2:.1f}', 'tip': f'{label}: {_fmt(value)}{unit}',
            'show_label': i % math.ceil(n / 7) == 0,          # najviše ~7 oznaka, bez preklapanja
        })
    ticks = []
    for k in range(int(round(vmax / step)) + 1):
        v = step * k
        ticks.append({'y': f'{top + ph - ph * v / vmax:.1f}', 'label': _fmt(v)})
    peak = max(items, key=lambda it: it[1]) if items else None
    return {
        'w': width, 'h': height, 'bars': bars, 'ticks': ticks, 'left': left, 'right': width - right,
        'base_y': f'{top + ph:.1f}', 'label_y': f'{height - 8:.1f}', 'unit': unit,
        'total': sum(v for _, v in items), 'peak': peak,
    }


def _fmt(v):
    v = round(v, 2)
    if v >= 10000:
        return f'{v / 1000:.0f}K'.replace('.', ',')
    if float(v).is_integer():
        return f'{int(v):,}'.replace(',', '.')
    return f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


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
