from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.formats import date_format
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.permissions import hiker_required
from clubs.models import Club

from . import services
from .forms import TourSearchForm
from .models import Tour, TourGuide, TourRegistration

SELECTION_KEY = 'tour_selection'
MAX_SELECTION = 10


def public_tours():
    """Ture vidljive javnosti (politika 4.4): OBJAVLJENE, odobrenog društva, polazak u narednih 30 dana."""
    now = timezone.now()
    return (Tour.objects
            .filter(status=Tour.Status.PUBLISHED, club__status=Club.Status.APPROVED,
                    start_at__gte=now, start_at__lte=now + timedelta(days=30))
            .select_related('club')
            .annotate(taken=Count('registrations', filter=Q(registrations__status=TourRegistration.Status.REGISTERED)))
            .annotate(free_spots=F('max_participants') - F('taken')))


def _selection(request):
    raw = request.session.get(SELECTION_KEY, [])
    return [i for i in raw if isinstance(i, int)][:MAX_SELECTION]


FEATURED_ON_HOME = 3


@require_GET
def home(request):
    """Početna: uvod, zbirne brojke i nekoliko najbližih tura (F01). Sve ture su na /ture/."""
    all_public = public_tours()
    agg = Tour.objects.filter(pk__in=all_public.values('pk')).aggregate(km=Sum('length_km'), up=Sum('elevation_gain_m'))
    return render(request, 'tours/home.html', {
        'featured': all_public.order_by('start_at')[:FEATURED_ON_HOME],
        'selection': _selection(request),
        'stats': {
            'tours': all_public.count(),
            'clubs': Club.objects.filter(status=Club.Status.APPROVED).count(),
            'km': int(agg['km'] or 0),
            'elevation': int(agg['up'] or 0),
        },
    })


def _map_points(tours):
    """Tačke za mapu: samo javni podaci ture. Početak rute je pozicija pina.
    Tekst (naziv, društvo) se u pregledniku umeće isključivo kao tekst (textContent)."""
    points = []
    for t in tours:
        if isinstance(t.route, list) and len(t.route) >= 2:
            lat, lng = t.route[0]
            points.append({
                'id': t.pk, 'url': reverse('tours:detail', args=[t.pk]),
                'name': t.name, 'club': t.club.name, 'lat': lat, 'lng': lng,
                'date': date_format(timezone.localtime(t.start_at), 'D, d.m. · H:i'),
                'difficulty': t.difficulty, 'difficulty_label': t.get_difficulty_display(),
                'free': max(t.free_spots, 0), 'max': t.max_participants,
            })
    return points


@require_GET
def tour_list(request):
    """F01 + F02 - sve javne ture u narednih 30 dana: mapa sa pinovima, filteri i lista."""
    filtered = bool(request.GET)
    form = TourSearchForm(request.GET or None)
    tours = list((form.filter(public_tours()) if filtered else public_tours()).order_by('start_at'))
    points = _map_points(tours)
    return render(request, 'tours/list.html', {
        'form': form, 'tours': tours, 'filtered': filtered, 'selection': _selection(request),
        'map_points': points, 'without_route': len(tours) - len(points),
    })


@require_GET
def tour_detail(request, pk):
    """F03 - detalji ture. Samo javno vidljive ture; ostale daju 404."""
    tour = get_object_or_404(public_tours(), pk=pk)
    guides = (TourGuide.objects.filter(tour=tour, status=TourGuide.Status.APPROVED)
              .select_related('user').order_by('user__last_name'))
    my_reg = None
    if request.user.is_authenticated:
        my_reg = TourRegistration.objects.filter(tour=tour, user=request.user, status__in=services.ACTIVE).first()
    return render(request, 'tours/detail.html', {
        'tour': tour,
        'guide_names': [g.user.get_full_name() for g in guides],   # politika 4.4: samo ime i prezime vodiča
        'my_reg': my_reg,
        'in_selection': tour.pk in _selection(request),
        'deadline_passed': timezone.now() >= tour.registration_deadline,
        'map_data': {'route': tour.route, 'name': tour.name},
        'start': start_point(tour),
    })


def start_point(tour):
    """Koordinate polaska (prva tačka rute) i linkovi za Google mape. Samo brojevi sa servera."""
    if not (isinstance(tour.route, list) and len(tour.route) >= 2):
        return None
    lat, lng = (float(c) for c in tour.route[0])
    q = f'{lat:.6f},{lng:.6f}'
    return {
        'lat': f'{lat:.6f}', 'lng': f'{lng:.6f}', 'text': f'{lat:.6f}, {lng:.6f}',
        'dms': f'{_dms(lat, "N", "S")} {_dms(lng, "E", "W")}',
        'maps': f'https://www.google.com/maps/search/?api=1&query={q}',
        'directions': f'https://www.google.com/maps/dir/?api=1&destination={q}',
    }


def _dms(v, pos, neg):
    hemi = pos if v >= 0 else neg
    v = abs(v)
    d = int(v); m = int((v - d) * 60); s = (v - d - m / 60) * 3600
    return f'{d}°{m:02d}\'{s:04.1f}"{hemi}'


@require_GET
def tour_gpx(request, pk):
    """Preuzimanje rute javne ture kao GPX (za Google My Maps, Wikiloc, Komoot, GPS uređaje).
    GPX generiše server iz provjerenih koordinata; tekst (naziv, društvo) je XML-escapiran."""
    from xml.sax.saxutils import escape

    from django.http import Http404, HttpResponse

    tour = get_object_or_404(public_tours(), pk=pk)
    if not (isinstance(tour.route, list) and len(tour.route) >= 2):
        raise Http404
    pts = ''.join(f'<trkpt lat="{float(lat):.6f}" lon="{float(lng):.6f}"/>' for lat, lng in tour.route)
    lat0, lng0 = tour.route[0]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<gpx version="1.1" creator="Frostbite" xmlns="http://www.topografix.com/GPX/1/1">'
           f'<metadata><name>{escape(tour.name)}</name><desc>{escape(tour.club.name)}</desc></metadata>'
           f'<wpt lat="{float(lat0):.6f}" lon="{float(lng0):.6f}"><name>Polazak: {escape(tour.meeting_point)}</name></wpt>'
           f'<trk><name>{escape(tour.name)}</name><trkseg>{pts}</trkseg></trk></gpx>')
    resp = HttpResponse(xml, content_type='application/gpx+xml; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="frostbite-tura-{tour.pk}.gpx"'
    return resp


# --- Odabir više tura (F10) -------------------------------------------------
@require_POST
def selection_add(request, pk):
    tour = get_object_or_404(public_tours(), pk=pk)
    sel = _selection(request)
    if tour.pk not in sel:
        if len(sel) >= MAX_SELECTION:
            messages.error(request, f'Možete odabrati najviše {MAX_SELECTION} tura.')
        else:
            sel.append(tour.pk)
            request.session[SELECTION_KEY] = sel
            messages.success(request, f'„{tour.name}“ je dodana u odabir.')
    return redirect('tours:detail', pk=tour.pk)


@require_POST
def selection_remove(request, pk):
    sel = [i for i in _selection(request) if i != pk]
    request.session[SELECTION_KEY] = sel
    if request.POST.get('back') == 'detail':
        return redirect('tours:detail', pk=pk)
    return redirect('tours:selection')


@require_GET
def selection(request):
    sel = _selection(request)
    tours = list(public_tours().filter(pk__in=sel).order_by('start_at'))
    if len(tours) != len(sel):                          # izbaci ture koje više nisu javne
        request.session[SELECTION_KEY] = [t.pk for t in tours]
    return render(request, 'tours/selection.html', {'tours': tours})


@hiker_required
@require_POST
def selection_confirm(request):
    """F10 - prijava na sve odabrane ture odjednom; svaka se provjerava zasebno."""
    results = []
    for tour_id in _selection(request):
        tour = Tour.objects.filter(pk=tour_id).only('name').first()
        try:
            reg = services.register(request, tour_id)
            text = 'prijavljeni ste' if reg.status == TourRegistration.Status.REGISTERED else 'na listi čekanja'
            results.append((tour.name if tour else '?', True, text))
        except services.RegistrationError as e:
            results.append((tour.name if tour else '?', False, str(e)))
    request.session[SELECTION_KEY] = []
    return render(request, 'tours/selection_result.html', {'results': results})


# --- Moje prijave (F11, F12) ------------------------------------------------
@hiker_required
@require_GET
def my_registrations(request):
    regs = (TourRegistration.objects.filter(user=request.user)
            .select_related('tour', 'tour__club').order_by('-tour__start_at'))
    now = timezone.now()
    upcoming = [r for r in regs if r.tour.start_at >= now and r.status != TourRegistration.Status.CANCELLED]
    history = [r for r in regs if r not in upcoming]
    for r in upcoming:
        r.can_cancel = (r.tour.status in (Tour.Status.PUBLISHED, Tour.Status.CLOSED)
                        and now < r.tour.registration_deadline)
    return render(request, 'tours/my_registrations.html', {'upcoming': upcoming, 'history': history})


@hiker_required
@require_POST
def cancel_registration(request, pk):
    try:
        reg = services.cancel(request, pk)
        messages.success(request, f'Odjavljeni ste sa ture „{reg.tour.name}“.')
    except services.RegistrationError as e:
        messages.error(request, str(e))
    return redirect('tours:my_registrations')


@hiker_required
@require_http_methods(['POST'])
def register_single(request, pk):
    """Prijava na jednu turu direktno sa stranice detalja."""
    try:
        reg = services.register(request, pk)
        if reg.status == TourRegistration.Status.REGISTERED:
            messages.success(request, 'Prijavljeni ste na turu.')
        else:
            messages.success(request, 'Tura je popunjena: upisani ste na listu čekanja.')
    except services.RegistrationError as e:
        messages.error(request, str(e))
    return redirect('tours:my_registrations')
