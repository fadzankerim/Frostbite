"""Funkcionalnosti sistemskog admina (F29-F31) - HTML stranice. Pravila su u panel.system_service."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.permissions import system_admin_required

from . import system_service as svc
from .charts import column_chart
from .forms import AuditFilterForm, UserSearchForm

CLUB_TRANSITIONS = svc.CLUB_TRANSITIONS
SECURITY_ACTIONS = svc.SECURITY_ACTIONS


@system_admin_required
@require_GET
def clubs(request):
    """F29."""
    pending, others = svc.clubs()
    return render(request, 'panel/sys_clubs.html', {'pending': pending, 'others': others})


@system_admin_required
@require_POST
def club_decide(request, pk, action):
    try:
        club = svc.decide_club(request, pk, action)
        messages.success(request, f'Društvo „{club.name}“: {club.get_status_display().lower()}.')
    except svc.AdminActionError as e:
        messages.error(request, str(e))
    return redirect('panel:sys_clubs')


@system_admin_required
@require_GET
def users(request):
    """F30 - pregled naloga (samo ime, prezime, email, status)."""
    form = UserSearchForm(request.GET or None)
    q = form.cleaned_data['q'] if form.is_valid() else ''
    return render(request, 'panel/sys_users.html',
                  {'form': form, 'page': svc.users_page(q, request.GET.get('page')), 'now': timezone.now()})


@system_admin_required
@require_POST
def user_toggle(request, pk):
    try:
        target = svc.toggle_user(request, pk)
        messages.success(request, f'Nalog {target.email} je {"deblokiran" if target.is_active else "blokiran"}.')
    except svc.AdminActionError as e:
        messages.error(request, str(e))
    return redirect('panel:sys_users')


@system_admin_required
@require_GET
def audit_log(request):
    """F31 - evidencija aktivnosti (samo čitanje)."""
    form = AuditFilterForm(request.GET or None)
    action = form.cleaned_data['action'] if form.is_valid() else ''
    return render(request, 'panel/sys_audit.html', {'form': form, 'page': svc.audit_page(action, request.GET.get('page'))})


@system_admin_required
@require_GET
def dashboard(request):
    """Početna stranica sistemskog admina: analitika platforme i sigurnosni događaji."""
    d = svc.dashboard()
    tmax = max([c for _, c in d['tour_status']] + [1])
    return render(request, 'panel/sys_dashboard.html', {
        'tab': 'overview', 'heading': 'Pregled platforme',
        'kpi': d['kpi'], 'sec': d['sec'],
        'logins': column_chart(d['logins']), 'fails': column_chart(d['fails']),
        'tour_status': [(label, c, tmax) for label, c in d['tour_status']],
        'pending_clubs': d['pending_clubs'], 'events': d['events'],
    })
