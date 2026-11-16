"""Funkcionalnosti sistemskog admina (F29-F31). Sistemski admin NE vidi telefon, hitni kontakt
ni zdravstvene napomene (politika 4.5) - upiti učitavaju samo ime, prezime, email i status."""
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User
from accounts.permissions import system_admin_required
from audit.log import audit
from audit.models import AuditLog
from clubs.models import Club

from .forms import AuditFilterForm, UserSearchForm

CLUB_TRANSITIONS = {
    'approve': ([Club.Status.PENDING], Club.Status.APPROVED, 'DRUSTVO_ODOBRENO'),
    'reject': ([Club.Status.PENDING], Club.Status.REJECTED, 'DRUSTVO_ODBIJENO'),
    'suspend': ([Club.Status.APPROVED], Club.Status.SUSPENDED, 'DRUSTVO_SUSPENDOVANO'),
}


@system_admin_required
@require_GET
def clubs(request):
    """F29."""
    qs = Club.objects.select_related('created_by').only(
        'name', 'city', 'status', 'created_at', 'created_by__first_name', 'created_by__last_name', 'created_by__email')
    return render(request, 'panel/sys_clubs.html', {
        'pending': qs.filter(status=Club.Status.PENDING).order_by('created_at'),
        'others': qs.exclude(status=Club.Status.PENDING).order_by('name'),
    })


@system_admin_required
@require_POST
def club_decide(request, pk, action):
    if action not in CLUB_TRANSITIONS:
        raise Http404
    allowed, new, audit_action = CLUB_TRANSITIONS[action]
    with transaction.atomic():
        club = get_object_or_404(Club.objects.select_for_update(), pk=pk)
        if club.status not in allowed:
            messages.error(request, 'Ova promjena statusa nije dozvoljena.')
            return redirect('panel:sys_clubs')
        club.status = new
        club.save(update_fields=['status'])
    audit(request, audit_action, 'club', club.pk)
    messages.success(request, f'Društvo „{club.name}“: {club.get_status_display().lower()}.')
    return redirect('panel:sys_clubs')


@system_admin_required
@require_GET
def users(request):
    """F30 - pregled naloga (samo ime, prezime, email, status)."""
    form = UserSearchForm(request.GET or None)
    qs = User.objects.only('email', 'first_name', 'last_name', 'is_active', 'is_system_admin', 'date_joined', 'locked_until')
    if form.is_valid() and form.cleaned_data['q']:
        q = form.cleaned_data['q']
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    page = Paginator(qs.order_by('last_name', 'first_name'), 25).get_page(request.GET.get('page'))
    return render(request, 'panel/sys_users.html', {'form': form, 'page': page, 'now': timezone.now()})


def _kill_sessions(user):
    """Poništava sve sesije korisnika (politika 4.6: blokiran korisnik gubi aktivne sesije)."""
    for s in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if s.get_decoded().get('_auth_user_id') == str(user.pk):
            s.delete()


@system_admin_required
@require_POST
def user_toggle(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, 'Ne možete blokirati vlastiti nalog.')          # ograničenje 5
        return redirect('panel:sys_users')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    if not target.is_active:
        _kill_sessions(target)
    audit(request, 'NALOG_DEBLOKIRAN' if target.is_active else 'NALOG_BLOKIRAN', 'user', target.pk)
    messages.success(request, f'Nalog {target.email} je {"deblokiran" if target.is_active else "blokiran"}.')
    return redirect('panel:sys_users')


@system_admin_required
@require_GET
def audit_log(request):
    """F31 - evidencija aktivnosti (samo čitanje)."""
    form = AuditFilterForm(request.GET or None)
    qs = AuditLog.objects.select_related('user').only(
        'action', 'entity', 'entity_id', 'details', 'ip', 'created_at', 'user__email')
    if form.is_valid() and form.cleaned_data['action']:
        qs = qs.filter(action__icontains=form.cleaned_data['action'])
    page = Paginator(qs.order_by('-created_at'), 50).get_page(request.GET.get('page'))
    return render(request, 'panel/sys_audit.html', {'form': form, 'page': page})


SECURITY_ACTIONS = ['LOGIN_NEUSPJEH', 'NALOG_ZAKLJUCAN', 'LOGIN_ZAKLJUCAN', 'LOGIN_BLOKIRAN', 'NALOG_BLOKIRAN',
                    'REGISTRACIJA_DUPLIKAT']


@system_admin_required
@require_GET
def dashboard(request):
    """Početna stranica sistemskog admina: analitika platforme i sigurnosni događaji.
    Samo zbirni podaci - bez ličnih podataka korisnika."""
    from datetime import timedelta

    from tours.models import Tour, TourRegistration

    from .charts import column_chart, daily_series

    now = timezone.now()
    today = timezone.localdate()
    week = now - timedelta(days=7)
    users = User.objects.all()
    logs = AuditLog.objects.all()

    tour_status = [(label, Tour.objects.filter(status=value).count()) for value, label in Tour.Status.choices]
    tmax = max([c for _, c in tour_status] + [1])
    ctx = {
        'tab': 'overview', 'heading': 'Pregled platforme',
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
        'logins': column_chart(daily_series(logs.filter(action='LOGIN_USPJEH'), 'created_at', 14, today)),
        'fails': column_chart(daily_series(logs.filter(action__in=['LOGIN_NEUSPJEH', 'LOGIN_ZAKLJUCAN', 'LOGIN_BLOKIRAN']),
                                           'created_at', 14, today)),
        'tour_status': [(label, c, tmax) for label, c in tour_status],
        'pending_clubs': Club.objects.filter(status=Club.Status.PENDING).order_by('created_at')[:5],
        'events': logs.filter(action__in=SECURITY_ACTIONS).select_related('user').only(
            'action', 'created_at', 'ip', 'details', 'user__email').order_by('-created_at')[:8],
    }
    return render(request, 'panel/sys_dashboard.html', ctx)
