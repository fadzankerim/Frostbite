"""Upiti za ture, zajednički za API (vidljivost tura i odabir u sesiji)."""
from datetime import timedelta

from django.db.models import Count, F, Q
from django.utils import timezone

from clubs.models import Club

from .models import Tour, TourRegistration

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


def selection(request):
    """ID-jevi odabranih tura iz sesije (samo cijeli brojevi, najviše MAX_SELECTION)."""
    raw = request.session.get(SELECTION_KEY, [])
    return [i for i in raw if isinstance(i, int)][:MAX_SELECTION]
