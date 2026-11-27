"""Događaji koji izazivaju obavještenja. Servisi ih pozivaju UNUTAR svoje transakcije, pa red u
outboxu nastaje samo ako radnja uspije.

Svaki događaj radi u vlastitom savepointu: greška pri pravljenju obavještenja se loguje i ne ruši
glavnu radnju (prijava na turu je važnija od emaila o njoj).

U kontekst idu samo podaci koji smiju u email: nazivi, termin, mjesto polaska, imena i linkovi.
Nikad telefoni, hitni kontakti ni zdravstvene napomene.
"""
import functools
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from badges.rules import club_admin_users
from clubs.models import ClubGuide, ClubMembership
from tours.models import TourGuide, TourRegistration

from .models import Outbox
from .services import link, notify, tour_context

log = logging.getLogger(__name__)
R = TourRegistration.Status
LATE_CANCEL = timedelta(hours=24)


def safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            with transaction.atomic():
                fn(*args, **kwargs)
        except Exception:
            log.exception('Obavještenje nije upisano (%s)', fn.__name__)
    return wrapper


def _recently(user, template, hours=1):
    """Da li je korisnik već dobio ovo obavještenje u posljednjih `hours` sati. Sprečava da treća
    strana (pokušaji prijave ili registracije s tuđim emailom) zatrpa vlasnika naloga emailovima."""
    since = timezone.now() - timedelta(hours=hours)
    return Outbox.objects.filter(user=user, template=template, created_at__gte=since).exists()


def _guides(tour):
    return [g.user for g in TourGuide.objects.filter(tour=tour, status=TourGuide.Status.APPROVED).select_related('user')]


def _registered(tour):
    return TourRegistration.objects.filter(tour=tour, status=R.REGISTERED).count()


def _valid_members(club):
    today = timezone.localdate()
    from django.db.models import Q
    return [m.user for m in ClubMembership.objects.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today), club=club,
        status=ClubMembership.Status.APPROVED, user__is_active=True).select_related('user')]


def _participants_change(reg, action, urgent=False):
    tour = reg.tour
    ctx = tour_context(tour, name=reg.user.get_full_name(), action=action, action_lower=action.lower(),
                       registered=_registered(tour), max=tour.max_participants, url=link(f'/vodic/ture/{tour.pk}'))
    notify(_guides(tour), 'ucesnici', 'ucesnici_promjena', ctx, urgent=urgent)


# --- planinar ------------------------------------------------------------------------
@safe
def registration_created(reg):
    tour = reg.tour
    notify([reg.user], 'moje_ture', 'prijava_potvrda',
           tour_context(tour, waitlist=reg.status == R.WAITLIST, url=link(f'/ture/{tour.pk}')))
    if reg.status == R.REGISTERED:
        _participants_change(reg, 'Prijava')
        if _registered(tour) >= tour.max_participants:
            notify(club_admin_users(tour.club), 'drustvo', 'tura_popunjena',
                   tour_context(tour, url=link(f'/upravljanje/{tour.club_id}/ture/{tour.pk}')))


@safe
def registration_cancelled(reg, was_registered, promoted):
    tour = reg.tour
    if was_registered:
        _participants_change(reg, 'Odjava', urgent=tour.start_at - timezone.now() <= LATE_CANCEL)
    if promoted:
        notify([promoted.user], 'moje_ture', 'lista_cekanja_mjesto', tour_context(tour, url=link('/moje-prijave')))


@safe
def tour_published(tour):
    ctx = tour_context(tour, url=link(f'/ture/{tour.pk}'))
    notify(_valid_members(tour.club), 'nove_ture', 'nova_tura', ctx)
    if not TourGuide.objects.filter(tour=tour, status=TourGuide.Status.APPROVED).exists():
        guides = [g.user for g in ClubGuide.objects.filter(club=tour.club, is_active=True, user__is_active=True)
                  .select_related('user')]
        notify(guides, 'vodjenje', 'tura_bez_vodica', tour_context(tour, url=link('/vodic')))


@safe
def tour_cancelled(tour):
    regs = TourRegistration.objects.filter(tour=tour, status__in=[R.REGISTERED, R.WAITLIST]).select_related('user')
    notify([r.user for r in regs], 'moje_ture', 'tura_otkazana', tour_context(tour, url=link('/moje-prijave')))
    notify(_guides(tour), 'vodjenje', 'tura_otkazana', tour_context(tour, url=link('/vodic')))


@safe
def tour_changed(tour):
    regs = TourRegistration.objects.filter(tour=tour, status__in=[R.REGISTERED, R.WAITLIST]).select_related('user')
    ctx = tour_context(tour, url=link(f'/ture/{tour.pk}'))
    notify([r.user for r in regs], 'moje_ture', 'tura_izmijenjena', ctx)


@safe
def membership_requested(m):
    notify(club_admin_users(m.club), 'drustvo', 'clanstvo_zahtjev',
           {'club': m.club.name, 'name': m.user.get_full_name(), 'url': link(f'/upravljanje/{m.club_id}/clanovi')})


@safe
def membership_decided(m):
    notify([m.user], 'drustva', 'clanstvo_odluka',
           {'club': m.club.name, 'approved': m.status == ClubMembership.Status.APPROVED, 'url': link('/moja-clanstva')})


# --- vodič ---------------------------------------------------------------------------
@safe
def guide_applied(tg):
    tour = tg.tour
    notify(club_admin_users(tour.club), 'drustvo', 'vodic_prijava',
           tour_context(tour, name=tg.user.get_full_name(), url=link(f'/upravljanje/{tour.club_id}/ture/{tour.pk}')))


@safe
def guide_decided(tg):
    notify([tg.user], 'vodjenje', 'vodjenje_odluka',
           tour_context(tg.tour, approved=tg.status == TourGuide.Status.APPROVED, url=link('/vodic')))


@safe
def guide_assigned(tg):
    notify([tg.user], 'vodjenje', 'vodic_dodijeljen', tour_context(tg.tour, url=link(f'/vodic/ture/{tg.tour_id}')))


# --- društva -------------------------------------------------------------------------
@safe
def club_requested(club):
    admins = User.objects.filter(is_system_admin=True, is_active=True)
    notify(admins, 'zahtjevi_drustava', 'drustvo_zahtjev',
           {'club': club.name, 'city': club.city, 'url': link('/sistem/drustva')})


@safe
def club_decided(club, approved):
    notify([club.created_by], 'drustva', 'drustvo_odluka',
           {'club': club.name, 'approved': approved, 'url': link('/upravljanje' if approved else '/')})


# --- sigurnost (ne može se isključiti) ------------------------------------------------
@safe
def password_changed(user):
    notify([user], 'sigurnost', 'lozinka_promijenjena', {})


@safe
def account_locked(user):
    if not _recently(user, 'nalog_zakljucan'):
        notify([user], 'sigurnost', 'nalog_zakljucan', {'minutes': settings.LOCKOUT_MINUTES})


@safe
def account_blocked(user):
    notify([user], 'sigurnost', 'nalog_blokiran', {})


@safe
def duplicate_registration(email):
    """Vlasnik emaila saznaje za pokušaj; odgovor aplikacije ostaje isti (bez otkrivanja naloga)."""
    user = User.objects.filter(email=email).first()
    if user is not None and not _recently(user, 'registracija_postojeci'):
        notify([user], 'sigurnost', 'registracija_postojeci', {'url': link('/prijava')})
