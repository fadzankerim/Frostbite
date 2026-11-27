"""Javni API tura (/api/tours/) za React frontend.

Vidljivost (politika 4.4): samo public_tours(), tj. OBJAVLJENE ture
odobrenih društava sa polaskom u narednih 30 dana. Sve ostalo daje 404, isto kao nepostojeća tura.
Odgovori sadrže samo izričito nabrojana polja (bez created_by, učesnika i sl.); vodiči samo
imenom i prezimenom. Endpointi su samo za čitanje (GET); sve ostalo je 405.
"""
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from clubs.models import Club
from frostbite.api import ApiView, form_errors

from . import services
from .forms import TourSearchForm
from .models import Tour, TourGuide, TourRegistration
from .queries import public_tours, selection as _selection

MAX_TRACE_POINTS = 40


def _start(tour):
    route = tour.route
    if isinstance(route, list) and len(route) >= 2:
        lat, lng = route[0]
        return [float(lat), float(lng)]
    return None


def _trace(route):
    """Pojednostavljena ruta za sličicu na kartici (najviše MAX_TRACE_POINTS tačaka)."""
    if not (isinstance(route, list) and len(route) >= 2):
        return []
    step = max(1, -(-len(route) // MAX_TRACE_POINTS))
    pts = route[::step]
    if (len(route) - 1) % step:
        pts.append(route[-1])
    return [[round(float(a), 5), round(float(b), 5)] for a, b in pts]


def tour_summary(tour):
    return {
        'id': tour.pk,
        'name': tour.name,
        'club': {'id': tour.club_id, 'name': tour.club.name},
        'region': tour.region,
        'startAt': tour.start_at.isoformat(),
        'difficulty': {'code': tour.difficulty, 'label': tour.get_difficulty_display()},
        'lengthKm': float(tour.length_km),
        'elevationGainM': tour.elevation_gain_m,
        'durationH': float(tour.duration_h),
        'price': float(tour.price),
        'membersOnly': tour.members_only,
        'maxParticipants': tour.max_participants,
        'freeSpots': max(tour.free_spots, 0),
        'start': _start(tour),
        'trace': _trace(tour.route),
    }


class TourListView(ApiView):
    """F01 + F02 - javne ture sa filterima (?q, difficulty, club, date_from, date_to)."""
    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        allowed = {'q', 'difficulty', 'club', 'date_from', 'date_to'}
        data = {k: params.get(k) for k in allowed if params.get(k)}
        qs = public_tours()
        if data:
            form = TourSearchForm(data)
            if not form.is_valid():
                return Response({'errors': form_errors(form)}, status=400)
            qs = form.filter(qs)
        return Response({'results': [tour_summary(t) for t in qs.order_by('start_at')]})


class TourFiltersView(ApiView):
    """Vrijednosti za filtere: težine i odobrena društva."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'difficulties': [{'code': c, 'label': str(l)} for c, l in Tour.Difficulty.choices],
            'clubs': [{'id': c.pk, 'name': c.name}
                      for c in Club.objects.filter(status=Club.Status.APPROVED).order_by('name')],
        })


class TourStatsView(ApiView):
    """Zbirne brojke za početnu stranicu (isto kao Django početna)."""
    permission_classes = [AllowAny]

    def get(self, request):
        public = public_tours()
        agg = Tour.objects.filter(pk__in=public.values('pk')).aggregate(km=Sum('length_km'), up=Sum('elevation_gain_m'))
        return Response({
            'tours': public.count(),
            'clubs': Club.objects.filter(status=Club.Status.APPROVED).count(),
            'km': int(agg['km'] or 0),
            'elevation': int(agg['up'] or 0),
        })


class TourDetailView(ApiView):
    """F03 - detalji javne ture. Ostale ture daju 404."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        tour = get_object_or_404(public_tours(), pk=pk)
        guides = (TourGuide.objects.filter(tour=tour, status=TourGuide.Status.APPROVED)
                  .select_related('user').order_by('user__last_name'))
        my_reg = None
        user = request.user
        if user.is_authenticated:
            reg = TourRegistration.objects.filter(tour=tour, user=user, status__in=services.ACTIVE).first()
            if reg:
                my_reg = {'id': reg.pk, 'status': reg.status, 'label': reg.get_status_display()}
        route = tour.route if isinstance(tour.route, list) and len(tour.route) >= 2 else []
        return Response({
            **tour_summary(tour),
            'description': tour.description,
            'meetingPoint': tour.meeting_point,
            'registrationDeadline': tour.registration_deadline.isoformat(),
            'deadlinePassed': timezone.now() >= tour.registration_deadline,
            'requiredEquipment': tour.required_equipment,
            'route': [[float(a), float(b)] for a, b in route],
            'guides': [g.user.get_full_name() for g in guides],    # politika 4.4: samo ime i prezime
            'myRegistration': my_reg,
            'inSelection': tour.pk in _selection(request._request),
            # sistemski admin se ne prijavljuje na ture (F09-F14); server to ionako provjerava
            'canRegister': not (user.is_authenticated and user.is_system_admin),
            # tura samo za članove, a prijavljeni korisnik nema važeće članstvo: umjesto dugmeta
            # za prijavu prikazuje se objašnjenje (register() to ionako odbija)
            'membersOnlyBlocked': bool(tour.members_only and user.is_authenticated and not user.is_system_admin
                                       and not services.has_valid_membership(user, tour.club)),
        })
