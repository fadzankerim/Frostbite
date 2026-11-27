"""Pravila prijave i odjave sa ture (F10, F11; politika 4.3 ograničenja 3 i 4, politika 4.7).

Sve provjere se rade na serveru, unutar transakcije u kojoj je red ture zaključan
(SELECT ... FOR UPDATE). Tako dvije istovremene prijave ne mogu zauzeti isto posljednje mjesto.
"""
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from audit.log import audit
from badges import rules as badge_events
from badges.rules import club_admin_users
from badges.services import notify as notify_badges
from notifications import events as notifications
from clubs.models import Club, ClubMembership

from .models import Tour, TourGuide, TourRegistration

ACTIVE = [TourRegistration.Status.REGISTERED, TourRegistration.Status.WAITLIST]


class RegistrationError(Exception):
    pass


class RegistrationNotFound(RegistrationError):
    """Prijava ne postoji ili nije korisnikova (isti odgovor: 404, IDOR zaštita)."""


def has_valid_membership(user, club):
    today = timezone.localdate()
    return ClubMembership.objects.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today),
        user=user, club=club, status=ClubMembership.Status.APPROVED,
    ).exists()


def register(request, tour_id):
    """Prijavljuje request.user na turu. Vraća TourRegistration ili baca RegistrationError."""
    user = request.user
    if not user.is_authenticated or user.is_system_admin:
        raise RegistrationError('Ova radnja nije dozvoljena.')

    with transaction.atomic():
        tour = (Tour.objects.select_for_update()
                .filter(pk=tour_id, club__status=Club.Status.APPROVED).first())
        if tour is None or tour.status != Tour.Status.PUBLISHED:
            raise RegistrationError('Prijave na ovu turu nisu otvorene.')
        if timezone.now() >= tour.registration_deadline:
            raise RegistrationError('Rok za prijavu je istekao.')
        if tour.members_only and not has_valid_membership(user, tour.club):
            raise RegistrationError('Tura je samo za članove društva sa važećim članstvom.')
        if TourGuide.objects.filter(tour=tour, user=user, status=TourGuide.Status.APPROVED).exists():
            raise RegistrationError('Vodič se ne može prijaviti kao učesnik ture koju vodi.')
        if TourRegistration.objects.filter(tour=tour, user=user, status__in=ACTIVE).exists():
            raise RegistrationError('Već ste prijavljeni na ovu turu.')

        taken = TourRegistration.objects.filter(tour=tour, status=TourRegistration.Status.REGISTERED).count()
        status = (TourRegistration.Status.REGISTERED if taken < tour.max_participants
                  else TourRegistration.Status.WAITLIST)
        try:
            reg = TourRegistration.objects.create(tour=tour, user=user, status=status)
        except IntegrityError:
            raise RegistrationError('Već ste prijavljeni na ovu turu.')
        notifications.registration_created(reg)

    audit(request, 'TURA_PRIJAVA', 'tour_registration', reg.pk, details=f'tura={tour.pk} status={status}')
    notify_badges(badge_events.REGISTRATION, [user, *club_admin_users(tour.club)])
    return reg


def cancel(request, registration_id):
    """Odjava vlastite prijave (ograničenje 4). Ako se oslobodi mjesto, prvi sa liste čekanja
    postaje prijavljen."""
    user = request.user
    with transaction.atomic():
        reg = (TourRegistration.objects.select_related('tour')
               .filter(pk=registration_id, user=user, status__in=ACTIVE).first())
        if reg is None:
            raise RegistrationNotFound('Prijava nije pronađena.')
        tour = Tour.objects.select_for_update().get(pk=reg.tour_id)
        if tour.status not in (Tour.Status.PUBLISHED, Tour.Status.CLOSED) or timezone.now() >= tour.registration_deadline:
            raise RegistrationError('Rok za odjavu je istekao.')

        was_registered = reg.status == TourRegistration.Status.REGISTERED
        reg.status = TourRegistration.Status.CANCELLED
        reg.save(update_fields=['status', 'updated_at'])

        promoted = None
        if was_registered:
            promoted = (TourRegistration.objects.select_for_update()
                        .filter(tour=tour, status=TourRegistration.Status.WAITLIST)
                        .order_by('created_at').first())
            if promoted:
                promoted.status = TourRegistration.Status.REGISTERED
                promoted.save(update_fields=['status', 'updated_at'])
        notifications.registration_cancelled(reg, was_registered, promoted)

    audit(request, 'TURA_ODJAVA', 'tour_registration', reg.pk, details=f'tura={tour.pk}')
    if promoted:
        audit(request, 'TURA_SA_LISTE_CEKANJA', 'tour_registration', promoted.pk, user=promoted.user,
              details=f'tura={tour.pk}')
        notify_badges(badge_events.REGISTRATION, club_admin_users(tour.club))
    return reg
