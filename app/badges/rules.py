"""Pravila za bedževe. Svako pravilo računa napredak iz postojećih tabela; ništa se ne broji na
klijentu. Bedž je zaslužen kad je metric(user) >= goal.

„Završena tura“ znači prisustvo koje je evidentirao vodič (attendance = PRISUSTVOVAO), ne sama
prijava, pa se bedž ne može „nabiti“ prijavama i odjavama.
"""
from dataclasses import dataclass
from typing import Callable

from django.db.models import Count, F, Q, Sum

from accounts.models import User
from audit.models import AuditLog
from clubs.models import Club, ClubAdmin, ClubMembership
from tours.models import Tour, TourGuide, TourRegistration, TourReport

# Događaji koje servisi prijavljuju (badges.services.notify).
REGISTRATION = 'registration'      # prijava na turu ili prelazak s liste čekanja
ATTENDANCE = 'attendance'          # vodič evidentirao prisustvo
REPORT = 'report'                  # vodič predao izvještaj (tura ODRŽANA)
PUBLISH = 'publish'                # admin društva objavio turu
MEMBERSHIP = 'membership'          # odobreno članstvo
CLUB_DECISION = 'club_decision'    # sistemski admin odlučio o zahtjevu društva

CLUB_DECISION_ACTIONS = ['DRUSTVO_ODOBRENO', 'DRUSTVO_ODBIJENO']


def _hiker(user):
    return not user.is_system_admin


def _attended(user):
    return TourRegistration.objects.filter(user=user, attendance=TourRegistration.Attendance.PRESENT)


def _admin_clubs(user):
    # i suspendovano društvo je jednom bilo odobreno, pa njegova istorija vrijedi
    return Club.objects.filter(admins__user=user, status__in=[Club.Status.APPROVED, Club.Status.SUSPENDED])


def active_registrations(user):
    if not _hiker(user):
        return 0
    return TourRegistration.objects.filter(
        user=user, status__in=[TourRegistration.Status.REGISTERED, TourRegistration.Status.WAITLIST]).count()


def attended_count(user):
    return _attended(user).count() if _hiker(user) else 0


def attended_elevation(user):
    if not _hiker(user):
        return 0
    return _attended(user).aggregate(s=Sum('tour__elevation_gain_m'))['s'] or 0


def attended_difficulties(user):
    if not _hiker(user):
        return 0
    return _attended(user).values('tour__difficulty').distinct().count()


def approved_memberships(user):
    if not _hiker(user):
        return 0
    return ClubMembership.objects.filter(
        user=user, status__in=[ClubMembership.Status.APPROVED, ClubMembership.Status.EXPIRED]).count()


def led_done_tours(user):
    if not _hiker(user):
        return 0
    return Tour.objects.filter(status=Tour.Status.DONE, guide_assignments__user=user,
                               guide_assignments__status=TourGuide.Status.APPROVED).distinct().count()


def reports_count(user):
    return TourReport.objects.filter(guide=user).count() if _hiker(user) else 0


def approved_clubs(user):
    return _admin_clubs(user).count() if _hiker(user) else 0


def published_tours(user):
    if not _hiker(user):
        return 0
    return Tour.objects.filter(club__in=_admin_clubs(user), status__in=[
        Tour.Status.PUBLISHED, Tour.Status.CLOSED, Tour.Status.DONE]).count()


def full_tours(user):
    """Ima li društvo turu popunjenu do kapaciteta (prijavljeni, bez liste čekanja): 0 ili 1."""
    if not _hiker(user):
        return 0
    n = Count('registrations', filter=Q(registrations__status=TourRegistration.Status.REGISTERED))
    return int(Tour.objects.filter(club__in=_admin_clubs(user)).exclude(status=Tour.Status.DRAFT)
               .annotate(n=n).filter(n__gte=F('max_participants')).exists())


def club_attendees(user):
    if not _hiker(user):
        return 0
    return TourRegistration.objects.filter(tour__club__in=_admin_clubs(user),
                                           attendance=TourRegistration.Attendance.PRESENT).count()


def club_decisions(user):
    if not user.is_system_admin:
        return 0
    return AuditLog.objects.filter(user=user, action__in=CLUB_DECISION_ACTIONS).count()


@dataclass(frozen=True)
class Rule:
    code: str
    metric: Callable
    goal: int
    events: frozenset


def _r(code, metric, goal, *events):
    return Rule(code, metric, goal, frozenset(events))


RULES = [
    # planinar
    _r('prvi-korak', active_registrations, 1, REGISTRATION),
    _r('prvi-vrh', attended_count, 1, ATTENDANCE),
    _r('planinar-5', attended_count, 5, ATTENDANCE),
    _r('planinar-10', attended_count, 10, ATTENDANCE),
    _r('planinar-25', attended_count, 25, ATTENDANCE),
    _r('visinac-5000', attended_elevation, 5000, ATTENDANCE),
    _r('visinac-10000', attended_elevation, 10000, ATTENDANCE),
    _r('svestrani', attended_difficulties, len(Tour.Difficulty.choices), ATTENDANCE),
    _r('clan-drustva', approved_memberships, 1, MEMBERSHIP),
    # vodič
    _r('prvi-put-na-celu', led_done_tours, 1, REPORT),
    _r('iskusni-vodic-5', led_done_tours, 5, REPORT),
    _r('iskusni-vodic-20', led_done_tours, 20, REPORT),
    _r('uredan-dnevnik', reports_count, 10, REPORT),
    # admin društva
    _r('osnivac', approved_clubs, 1, CLUB_DECISION),
    _r('prva-objava', published_tours, 1, PUBLISH),
    _r('puna-kuca', full_tours, 1, REGISTRATION),
    _r('sto-planinara', club_attendees, 100, ATTENDANCE),
    # sistemski admin
    _r('cuvar-planine', club_decisions, 1, CLUB_DECISION),
    _r('budno-oko', club_decisions, 50, CLUB_DECISION),
]
RULES_BY_CODE = {r.code: r for r in RULES}


def club_admin_users(club):
    return list(User.objects.filter(pk__in=ClubAdmin.objects.filter(club=club).values('user')))
