"""Centralna pravila pristupa (sigurnosna politika, poglavlje 4).

Pravilo za sve view-ove: objekat koji korisnik ne smije vidjeti dohvata se kroz
OGRANIČEN queryset, tako da je odgovor 404 - isti kao za nepostojeći objekat.
Time se ne otkriva ni postojanje tuđih tura, društava ili prijava.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from clubs.models import Club


def admin_clubs(user):
    """Odobrena društva kojima korisnik upravlja (ograničenje 2)."""
    if not user.is_authenticated:
        return Club.objects.none()
    return Club.objects.filter(admins__user=user, status=Club.Status.APPROVED)


def guide_clubs(user):
    """Odobrena društva u kojima je korisnik aktivan vodič (ograničenje 2)."""
    if not user.is_authenticated:
        return Club.objects.none()
    return Club.objects.filter(guides__user=user, guides__is_active=True, status=Club.Status.APPROVED)


def is_club_admin(user):
    return admin_clubs(user).exists()


def is_guide(user):
    return guide_clubs(user).exists()


def system_admin_required(view):
    """Samo sistemski admin (F29-F31)."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_system_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def hiker_required(view):
    """Funkcionalnosti planinara (F09-F14): prijavljen korisnik koji NIJE sistemski admin."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_system_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def club_admin_required(view):
    """Admin društva (F18, F21-F28, ograničenje 2). Društvo iz URL-a se dohvata SAMO iz
    društava kojima korisnik upravlja - tuđe društvo daje 404. View dobija argument `club`."""
    from django.shortcuts import get_object_or_404

    @login_required
    @wraps(view)
    def wrapper(request, club_pk, *args, **kwargs):
        club = get_object_or_404(admin_clubs(request.user), pk=club_pk)
        return view(request, club, *args, **kwargs)
    return wrapper


def guide_required(view):
    """Vodič u barem jednom odobrenom društvu (F15-F20)."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_guide(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper
