"""Javni API društava (/api/clubs/). Samo odobrena društva; ostala daju 404. Samo GET."""
from collections import Counter

from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from frostbite.api import ApiView
from tours.api import tour_summary
from tours.views import public_tours

from .models import ClubMembership
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
        membership = None
        if request.user.is_authenticated:
            m = ClubMembership.objects.filter(club=club, user=request.user).order_by('-created_at').first()
            if m:
                membership = {'status': m.status, 'label': m.get_status_display(),
                              'validUntil': m.valid_until.isoformat() if m.valid_until else None}
        return Response({
            **club_summary(club, len(tours)),
            'email': club.email,
            'phone': club.phone,
            'tours': [tour_summary(t) for t in tours],
            'membership': membership,
        })
