"""UI pomoćnici: ikonice iz lokalnog SVG sprite-a (Lucide) i oznake težine."""
import re

from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()
_NAME = re.compile(r'^[a-z0-9-]+$')


@register.simple_tag
def icon(name, cls=''):
    if not _NAME.match(name):           # ime ikonice dolazi iz predloška, nikad od korisnika
        return ''
    return format_html('<svg class="icon {}" aria-hidden="true" focusable="false"><use href="{}#{}"></use></svg>',
                       cls, static('icons/sprite.svg'), name)


@register.filter
def difficulty_class(value):
    return {'LAKA': 'd-easy', 'SREDNJA': 'd-medium', 'TESKA': 'd-hard', 'VRLO_TESKA': 'd-extreme'}.get(value, '')


# --- Generisana ilustracija ture -------------------------------------------
# Pejzaž (nebo + tri sloja planina) obojen prema težini, sa ucrtanom trasom rute.
# Sve vrijednosti su brojevi koje generiše server - nema korisničkog teksta u SVG-u.
import random  # noqa: E402

from django.utils.safestring import mark_safe  # noqa: E402

PALETTES = {
    'LAKA':       ('#dcebd9', '#f4f1e8', ['#a9c39a', '#7a9b62', '#4b6b3e'], '#f2c94c'),
    'SREDNJA':    ('#f6e3bd', '#fbf4e4', ['#cdb98a', '#9f8f55', '#5f6a3c'], '#f2a93b'),
    'TESKA':      ('#f3d2c0', '#fbede4', ['#c9a08c', '#946f5f', '#4f4648'], '#e07a4f'),
    'VRLO_TESKA': ('#d9cfe2', '#f1ecf3', ['#aa9db6', '#6f607d', '#3a3347'], '#f4f1ea'),
}


def _ridge(rng, w, h, base, amp, peaks):
    xs = sorted(rng.uniform(0, w) for _ in range(peaks))
    pts = [(0, base + rng.uniform(-amp, amp) * .3)]
    for i, x in enumerate(xs):
        y = base - amp * rng.uniform(.35, 1) if i % 2 == 0 else base - amp * rng.uniform(0, .35)
        pts.append((x, y))
    pts.append((w, base + rng.uniform(-amp, amp) * .3))
    return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + f' L{w},{h} L0,{h} Z'


def _route_points(route, w, h, pad_x, top, bottom):
    lats = [p[0] for p in route]; lngs = [p[1] for p in route]
    la0, la1, lo0, lo1 = min(lats), max(lats), min(lngs), max(lngs)
    span = max(la1 - la0, lo1 - lo0, 1e-6)
    sw, sh = w - 2 * pad_x, bottom - top
    scale = min(sw, sh) / span
    ox = pad_x + (sw - (lo1 - lo0) * scale) / 2
    oy = top + (sh - (la1 - la0) * scale) / 2
    return [(ox + (lng - lo0) * scale, oy + (la1 - lat) * scale) for lat, lng in route]


@register.simple_tag
def tour_art(tour, size='card'):
    w, h = (320, 140) if size == 'card' else (960, 220)
    sky1, sky2, ridges, sun = PALETTES.get(tour.difficulty, PALETTES['SREDNJA'])
    rng = random.Random(tour.pk * 7919 + 17)
    gid = f'sky{tour.pk}{size[0]}'
    parts = [f'<svg class="tour-art" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">',
             f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{sky1}"/><stop offset="1" stop-color="{sky2}"/></linearGradient></defs>',
             f'<rect width="{w}" height="{h}" fill="url(#{gid})"/>',
             f'<circle cx="{rng.uniform(w * .6, w * .9):.0f}" cy="{h * .28:.0f}" r="{h * .12:.0f}" fill="{sun}" opacity=".85"/>']
    for i, color in enumerate(ridges):
        base = h * (.62 + i * .14)
        amp = h * (.42 - i * .1)
        parts.append(f'<path d="{_ridge(rng, w, h, base, amp, 5 + i * 2)}" fill="{color}"/>')
    if tour.difficulty == 'VRLO_TESKA' or getattr(tour, 'start_at', None) and tour.start_at.month in (12, 1, 2):
        parts.append(f'<path d="{_ridge(rng, w, h, h * .5, h * .38, 5)}" fill="#ffffff" opacity=".25"/>')
    route = tour.route if isinstance(tour.route, list) and len(tour.route) >= 2 else None
    if route:
        pts = _route_points(route, w, h, w * .18, h * .16, h * .84)
        line = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        parts.append(f'<polyline points="{line}" fill="none" stroke="#1f2a24" stroke-opacity=".35" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
        parts.append(f'<polyline points="{line}" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-dasharray="1 5" stroke-linecap="round" stroke-linejoin="round"/>')
        (sx, sy), (ex, ey) = pts[0], pts[-1]
        parts.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="4.5" fill="#2f5d46" stroke="#fff" stroke-width="2"/>')
        parts.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4.5" fill="#b05a32" stroke="#fff" stroke-width="2"/>')
    parts.append('</svg>')
    return mark_safe(''.join(parts))


@register.filter
def status_class(value):
    return {'NACRT': '', 'OBJAVLJENA': 'pill-ok', 'PRIJAVE_ZATVORENE': 'pill-wait', 'ODRZANA': 'pill-info',
            'OTKAZANA': 'pill-err', 'PRIJAVLJEN': 'pill-ok', 'NA_LISTI_CEKANJA': 'pill-wait', 'ODJAVLJEN': '',
            'PRIJAVIO_SE': 'pill-wait', 'ODOBREN': 'pill-ok', 'ODBIJEN': 'pill-err', 'NA_CEKANJU': 'pill-wait',
            'ODOBRENO': 'pill-ok', 'ODBIJENO': 'pill-err', 'SUSPENDOVANO': 'pill-err'}.get(value, '')
