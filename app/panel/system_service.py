"""Pravila sistemskog admina (F29-F31; politike 4.5, 4.6, 4.8, ograničenje 5).

Koristi ga JSON API (api_system). Sistemski admin NE vidi
telefon, hitni kontakt ni zdravstvene napomene (politika 4.5): upiti učitavaju samo ime, prezime,
email i status naloga. Evidencija aktivnosti je samo za čitanje (tabela je append-only i u bazi).
"""
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import User
from audit.log import audit
from badges import rules as badge_events
from badges.rules import club_admin_users
from badges.services import notify as notify_badges
from notifications import events as notifications
from audit.models import AuditLog
from clubs.models import Club

CLUB_TRANSITIONS = {
    'approve': ([Club.Status.PENDING], Club.Status.APPROVED, 'DRUSTVO_ODOBRENO'),
    'reject': ([Club.Status.PENDING], Club.Status.REJECTED, 'DRUSTVO_ODBIJENO'),
    'suspend': ([Club.Status.APPROVED], Club.Status.SUSPENDED, 'DRUSTVO_SUSPENDOVANO'),
}
SECURITY_ACTIONS = ['LOGIN_NEUSPJEH', 'NALOG_ZAKLJUCAN', 'LOGIN_ZAKLJUCAN', 'LOGIN_BLOKIRAN', 'NALOG_BLOKIRAN',
                    'REGISTRACIJA_DUPLIKAT']
USERS_PER_PAGE = 25
AUDIT_PER_PAGE = 50


class AdminActionError(Exception):
    """Radnja nije dozvoljena u trenutnom stanju (poruka za korisnika)."""


def clubs():
    """F29 - društva: na čekanju (najstarija prva) i ostala."""
    qs = Club.objects.select_related('created_by').only(
        'name', 'city', 'status', 'created_at', 'created_by__first_name', 'created_by__last_name', 'created_by__email')
    return qs.filter(status=Club.Status.PENDING).order_by('created_at'), qs.exclude(status=Club.Status.PENDING).order_by('name')


def available_club_actions(club):
    return [a for a, (allowed, *_r) in CLUB_TRANSITIONS.items() if club.status in allowed]


def decide_club(request, pk, action):
    if action not in CLUB_TRANSITIONS:
        raise Http404
    allowed, new, audit_action = CLUB_TRANSITIONS[action]
    with transaction.atomic():
        club = get_object_or_404(Club.objects.select_for_update(), pk=pk)
        if club.status not in allowed:
            raise AdminActionError('Ova promjena statusa nije dozvoljena.')
        club.status = new
        club.save(update_fields=['status'])
        if action in ('approve', 'reject'):
            notifications.club_decided(club, approved=action == 'approve')
    audit(request, audit_action, 'club', club.pk)
    if action in ('approve', 'reject'):
        notify_badges(badge_events.CLUB_DECISION, [request.user, *club_admin_users(club)])
    return club


def users_page(q, page):
    """F30 - pregled naloga (samo ime, prezime, email, status)."""
    qs = User.objects.only('email', 'first_name', 'last_name', 'is_active', 'is_system_admin', 'date_joined', 'locked_until')
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    return Paginator(qs.order_by('last_name', 'first_name', 'pk'), USERS_PER_PAGE).get_page(page)


def kill_sessions(user):
    """Poništava sve sesije korisnika (politika 4.6: blokiran korisnik gubi aktivne sesije)."""
    for s in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if s.get_decoded().get('_auth_user_id') == str(user.pk):
            s.delete()


def toggle_user(request, pk):
    """Blokiranje/deblokiranje naloga. Vlastiti nalog se ne može blokirati (ograničenje 5)."""
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        raise AdminActionError('Ne možete blokirati vlastiti nalog.')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    if not target.is_active:
        kill_sessions(target)
        notifications.account_blocked(target)
    audit(request, 'NALOG_DEBLOKIRAN' if target.is_active else 'NALOG_BLOKIRAN', 'user', target.pk)
    return target


def audit_page(action, page):
    """F31 - evidencija aktivnosti (samo čitanje), najnovije prvo."""
    qs = AuditLog.objects.select_related('user').only(
        'action', 'entity', 'entity_id', 'details', 'ip', 'created_at', 'user__email')
    if action:
        qs = qs.filter(action__icontains=action)
    return Paginator(qs.order_by('-created_at', '-pk'), AUDIT_PER_PAGE).get_page(page)


def daily_counts(qs, days, today):
    from .charts import daily_series
    return daily_series(qs, 'created_at', days, today)


def dashboard():
    """Analitika platforme i sigurnosni događaji - samo zbirni podaci, bez ličnih podataka."""
    from tours.models import Tour, TourRegistration

    now = timezone.now()
    today = timezone.localdate()
    week = now - timedelta(days=7)
    users = User.objects.all()
    logs = AuditLog.objects.all()
    return {
        'kpi': {
            'users': users.count(),
            'new_users': users.filter(date_joined__gte=now - timedelta(days=30)).count(),
            'clubs': Club.objects.filter(status=Club.Status.APPROVED).count(),
            'pending_clubs': Club.objects.filter(status=Club.Status.PENDING).count(),
            'tours_active': Tour.objects.filter(status__in=[Tour.Status.PUBLISHED, Tour.Status.CLOSED], start_at__gte=now).count(),
            'registrations': TourRegistration.objects.filter(status=TourRegistration.Status.REGISTERED, tour__start_at__gte=now).count(),
        },
        'sec': {
            'failed': logs.filter(action='LOGIN_NEUSPJEH', created_at__gte=week).count(),
            'lockouts': logs.filter(action='NALOG_ZAKLJUCAN', created_at__gte=week).count(),
            'locked_now': users.filter(locked_until__gt=now).count(),
            'blocked': users.filter(is_active=False).count(),
            'pii': logs.filter(action='PRISTUP_LICNIM_PODACIMA', created_at__gte=week).count(),
        },
        'logins': daily_counts(logs.filter(action='LOGIN_USPJEH'), 14, today),
        'fails': daily_counts(logs.filter(action__in=['LOGIN_NEUSPJEH', 'LOGIN_ZAKLJUCAN', 'LOGIN_BLOKIRAN']), 14, today),
        'tour_status': [(label, Tour.objects.filter(status=value).count()) for value, label in Tour.Status.choices],
        'pending_clubs': list(Club.objects.filter(status=Club.Status.PENDING).order_by('created_at')[:5]),
        'events': list(logs.filter(action__in=SECURITY_ACTIONS).select_related('user').only(
            'action', 'created_at', 'ip', 'details', 'user__email').order_by('-created_at')[:8]),
    }
