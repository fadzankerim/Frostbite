"""API planinara za ture (F10, F11, F12): prijava i odjava, odabir više tura, moje prijave.

Sva pravila su u tours.services (transakcija + SELECT FOR UPDATE, lista čekanja, rokovi, članstvo,
vodič se ne prijavljuje na svoju turu). Odabir tura dijeli isti ključ sesije kao HTML stranice,
pa je korpa ista u starom i novom interfejsu.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from frostbite.api import ApiView, IsHiker

from . import services
from .api import tour_summary
from .models import Tour, TourRegistration
from .views import MAX_SELECTION, SELECTION_KEY, _selection, public_tours


def _reg_payload(reg):
    return {'id': reg.pk, 'status': reg.status, 'label': reg.get_status_display()}


class TourRegisterView(ApiView):
    """F10 - prijava na jednu turu. Ako je tura puna, prijava ide na listu čekanja."""
    permission_classes = [IsHiker]

    def post(self, request, pk):
        try:
            reg = services.register(request._request, pk)
        except services.RegistrationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_reg_payload(reg), status=status.HTTP_201_CREATED)


class MyRegistrationsView(ApiView):
    """F11 - vlastite prijave: predstojeće (sa mogućnošću odjave do roka) i historija."""
    permission_classes = [IsHiker]

    def get(self, request):
        regs = (TourRegistration.objects.filter(user=request.user)
                .select_related('tour', 'tour__club').order_by('-tour__start_at', '-created_at'))
        now = timezone.now()
        public_ids = set(public_tours().values_list('pk', flat=True))
        upcoming, history = [], []
        for r in regs:
            t = r.tour
            item = {
                **_reg_payload(r),
                'attendance': r.get_attendance_display() if r.attendance else None,
                'tour': {
                    'id': t.pk, 'name': t.name, 'startAt': t.start_at.isoformat(),
                    'club': {'id': t.club_id, 'name': t.club.name},
                    'difficulty': {'code': t.difficulty, 'label': t.get_difficulty_display()},
                    'cancelled': t.status == Tour.Status.CANCELLED,
                    'public': t.pk in public_ids,
                },
            }
            if t.start_at >= now and r.status != TourRegistration.Status.CANCELLED:
                item['canCancel'] = (t.status in (Tour.Status.PUBLISHED, Tour.Status.CLOSED)
                                     and now < t.registration_deadline)
                upcoming.append(item)
            else:
                history.append(item)
        upcoming.reverse()      # najbliža prva
        return Response({'upcoming': upcoming, 'history': history})


class CancelRegistrationView(ApiView):
    """F11 - odjava vlastite prijave do roka. Prvi sa liste čekanja automatski dobija mjesto."""
    permission_classes = [IsHiker]

    def post(self, request, pk):
        try:
            reg = services.cancel(request._request, pk)
        except services.RegistrationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': f'Odjavljeni ste sa ture „{reg.tour.name}“.'})


def _selection_payload(request):
    sel = _selection(request)
    tours = list(public_tours().filter(pk__in=sel).order_by('start_at'))
    if len(tours) != len(sel):                       # izbaci ture koje više nisu javne
        request.session[SELECTION_KEY] = [t.pk for t in tours]
    return {'max': MAX_SELECTION, 'ids': [t.pk for t in tours], 'tours': [tour_summary(t) for t in tours]}


class SelectionView(ApiView):
    """F10 - odabir više tura (korpa u sesiji). Dostupno i prije prijave na sistem."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(_selection_payload(request._request))

    def post(self, request):
        raw = request.data.get('tourId') if isinstance(request.data, dict) else None
        if not isinstance(raw, int) or isinstance(raw, bool):
            return Response({'detail': 'Neispravna tura.'}, status=status.HTTP_400_BAD_REQUEST)
        tour = get_object_or_404(public_tours(), pk=raw)
        sel = _selection(request._request)
        if tour.pk not in sel:
            if len(sel) >= MAX_SELECTION:
                return Response({'detail': f'Možete odabrati najviše {MAX_SELECTION} tura.'},
                                status=status.HTTP_400_BAD_REQUEST)
            request._request.session[SELECTION_KEY] = [*sel, tour.pk]
        return Response(_selection_payload(request._request))


class SelectionItemView(ApiView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        request._request.session[SELECTION_KEY] = [i for i in _selection(request._request) if i != pk]
        return Response(_selection_payload(request._request))


class SelectionConfirmView(ApiView):
    """F10 - prijava na sve odabrane ture odjednom; svaka se provjerava zasebno."""
    permission_classes = [IsHiker]

    def post(self, request):
        results = []
        for tour_id in _selection(request._request):
            tour = Tour.objects.filter(pk=tour_id).only('name').first()
            name = tour.name if tour else '?'
            try:
                reg = services.register(request._request, tour_id)
                results.append({'tourId': tour_id, 'name': name, 'ok': True, **_reg_payload(reg)})
            except services.RegistrationError as e:
                results.append({'tourId': tour_id, 'name': name, 'ok': False, 'detail': str(e)})
        request._request.session[SELECTION_KEY] = []
        return Response({'results': results})
