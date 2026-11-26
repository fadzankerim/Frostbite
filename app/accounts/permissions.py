"""Centralna pravila pristupa (sigurnosna politika, poglavlje 4).

Pravilo za sve API endpointe: objekat koji korisnik ne smije vidjeti dohvata se kroz
OGRANIČEN queryset, tako da je odgovor 404 - isti kao za nepostojeći objekat.
Time se ne otkriva ni postojanje tuđih tura, društava ili prijava.
"""
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
