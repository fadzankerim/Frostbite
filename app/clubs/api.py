"""Javni API društava (/api/clubs/). Samo odobrena društva; ostala daju 404. Samo GET."""
from collections import Counter

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from audit.log import audit
from frostbite.api import ApiView, IsHiker
from tours.api import tour_summary
from tours.views import public_tours

from .models import Club, ClubMembership
from .views import approved_clubs


def club_summary(club, tours_count):
    return {
        'id': club.pk,
        'name': club.name,
        'city': club.city,
        'description': club.description,
        'toursCount': tours_count,
    }


class ClubListView(ApiView):
    """F04 - lista odobrenih društava sa brojem javnih tura."""
    permission_classes = [AllowAny]

    def get(self, request):
        counts = Counter(public_tours().values_list('club_id', flat=True))
        return Response({'results': [club_summary(c, counts.get(c.pk, 0)) for c in approved_clubs().order_by('name')]})


class ClubDetailView(ApiView):
    """F04 - javni profil društva (kontakt društva je javan) i njegove javne ture."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        club = get_object_or_404(approved_clubs(), pk=pk)
        tours = list(public_tours().filter(club=club).order_by('start_at'))
        user = request.user
        membership = None
        can_request = not user.is_authenticated        # anonimni vidi dugme koje vodi na prijavu
        if user.is_authenticated:
            m = ClubMembership.objects.filter(club=club, user=user).order_by('-created_at').first()
            membership = _membership_payload(m) if m else None
            # novi zahtjev: samo planinar bez aktivnog zahtjeva ili članstva (odbijen/istekao može ponovo)
            active = ClubMembership.objects.filter(
                club=club, user=user, status__in=[ClubMembership.Status.REQUESTED, ClubMembership.Status.APPROVED])
            can_request = not user.is_system_admin and not active.exists()
        return Response({
            **club_summary(club, len(tours)),
            'email': club.email,
            'phone': club.phone,
            'tours': [tour_summary(t) for t in tours],
            'membership': membership,
            'canRequest': can_request,
        })


class MembershipRequestView(ApiView):
    """F13 - zahtjev za učlanjenje u odobreno društvo (najviše jedan aktivan po društvu)."""
    permission_classes = [IsHiker]

    def post(self, request, pk):
        club = get_object_or_404(approved_clubs(), pk=pk)
        try:
            with transaction.atomic():
                m = ClubMembership.objects.create(club=club, user=request.user)
        except IntegrityError:
            return Response({'detail': 'Već imate aktivan zahtjev ili članstvo u ovom društvu.'}, status=400)
        audit(request._request, 'CLANSTVO_ZAHTJEV', 'club_membership', m.pk, details=f'drustvo={club.pk}')
        return Response({'detail': 'Zahtjev za učlanjenje je poslan. Društvo će ga razmotriti.',
                         'membership': _membership_payload(m)}, status=201)


def _membership_payload(m):
    today = timezone.localdate()
    return {
        'id': m.pk, 'status': m.status, 'label': m.get_status_display(),
        'validUntil': m.valid_until.isoformat() if m.valid_until else None,
        'expired': bool(m.status == ClubMembership.Status.APPROVED and m.valid_until and m.valid_until < today),
        'createdAt': m.created_at.isoformat(),
    }


class MyMembershipsView(ApiView):
    """F14 - vlastita članstva i zahtjevi."""
    permission_classes = [IsHiker]

    def get(self, request):
        items = ClubMembership.objects.filter(user=request.user).select_related('club').order_by('-created_at')
        return Response({'results': [
            {**_membership_payload(m), 'club': {'id': m.club_id, 'name': m.club.name, 'city': m.club.city,
                                                 'public': m.club.status == Club.Status.APPROVED}}
            for m in items]})
