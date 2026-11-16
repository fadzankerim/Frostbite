"""Funkcionalnosti admina društva (F18, F21-F28), politika 4.3 ograničenje 2.

Svaki view dobija `club` iz club_admin_required (samo društva kojima korisnik upravlja),
i svaki objekat se traži UNUTAR tog društva - tuđe ture, vodiči i članstva daju 404.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import User
from accounts.permissions import admin_clubs, club_admin_required
from audit.log import audit
from clubs.models import ClubGuide, ClubMembership
from tours.models import Tour, TourGuide, TourRegistration

from .forms import AddGuideForm, ClubProfileForm, TourForm

EDITABLE = [Tour.Status.DRAFT, Tour.Status.PUBLISHED, Tour.Status.CLOSED]


def club_tour(club, pk, lock=False):
    qs = Tour.objects.filter(club=club)
    if lock:
        qs = qs.select_for_update()
    return get_object_or_404(qs, pk=pk)


@login_required
@require_GET
def choose_club(request):
    """Ako korisnik upravlja sa više društava, bira jedno."""
    clubs = list(admin_clubs(request.user))
    if len(clubs) == 1:
        return redirect('panel:club', club_pk=clubs[0].pk)
    if not clubs:
        return redirect('home')
    return render(request, 'panel/club_choose.html', {'clubs': clubs})


def _money(v):
    return round(float(v or 0), 2)


@club_admin_required
@require_GET
def club_dashboard(request, club):
    """Početna stranica admina društva: analitika (ture po fazama, vodiči, članovi, učesnici, prihod).
    Prihod je procjena (cijena x prisutni / prijavljeni) - plaćanje se ne odvija kroz aplikaciju."""
    from django.db.models import Exists, F, OuterRef, Sum

    from .charts import MONTHS, column_chart, last_months

    now = timezone.now()
    today = timezone.localdate()
    tours = Tour.objects.filter(club=club)
    present = Count('registrations', filter=Q(registrations__attendance=TourRegistration.Attendance.PRESENT))
    registered = Count('registrations', filter=Q(registrations__status=TourRegistration.Status.REGISTERED))
    has_guide = TourGuide.objects.filter(tour=OuterRef('pk'), status=TourGuide.Status.APPROVED)

    done = tours.filter(status=Tour.Status.DONE).annotate(present=present)
    active = (tours.filter(status__in=[Tour.Status.PUBLISHED, Tour.Status.CLOSED], start_at__gte=now)
              .annotate(taken=registered, guided=Exists(has_guide)).order_by('start_at'))
    active_list = list(active)

    earned = sum(_money(t.price) * t.present for t in done)
    expected = sum(_money(t.price) * t.taken for t in active_list)
    capacity = sum(t.max_participants for t in active_list)
    taken = sum(t.taken for t in active_list)

    months = last_months(today, 6)
    by_month_people, by_month_money = {}, {}
    for t in done:
        key = (timezone.localtime(t.start_at).year, timezone.localtime(t.start_at).month)
        by_month_people[key] = by_month_people.get(key, 0) + t.present
        by_month_money[key] = by_month_money.get(key, 0) + _money(t.price) * t.present
    label = lambda ym: f'{MONTHS[ym[1] - 1]} {str(ym[0])[2:]}'  # noqa: E731

    guides = ClubGuide.objects.filter(club=club, is_active=True).select_related('user')
    led = dict(TourGuide.objects.filter(tour__club=club, status=TourGuide.Status.APPROVED, tour__status=Tour.Status.DONE)
               .values_list('user').annotate(c=Count('id')).values_list('user', 'c'))
    guide_rows = sorted(((g.user.get_full_name(), led.get(g.user_id, 0)) for g in guides), key=lambda r: -r[1])
    gmax = max([c for _, c in guide_rows] + [1])

    return render(request, 'panel/club_dashboard.html', {
        'club': club, 'tab': 'overview',
        'phases': {
            'draft': tours.filter(status=Tour.Status.DRAFT).count(),
            'active': len(active_list),
            'done': done.count(),
            'cancelled': tours.filter(status=Tour.Status.CANCELLED).count(),
        },
        'money': {'earned': earned, 'expected': expected},
        'fill': {'taken': taken, 'capacity': capacity, 'pct': round(100 * taken / capacity) if capacity else 0},
        'guides_count': len(guide_rows),
        'unguided': [t for t in active_list if not t.guided],
        'guide_rows': [(n, c, gmax) for n, c in guide_rows],
        'members_count': ClubMembership.objects.filter(club=club, status=ClubMembership.Status.APPROVED)
                         .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).count(),
        'pending_members': ClubMembership.objects.filter(club=club, status=ClubMembership.Status.REQUESTED).count(),
        'pending_guides': TourGuide.objects.filter(tour__club=club, status=TourGuide.Status.APPLIED, tour__start_at__gte=now).count(),
        'upcoming': active_list[:6],
        'people_chart': column_chart([(label(m), by_month_people.get(m, 0)) for m in months]),
        'money_chart': column_chart([(label(m), round(by_month_money.get(m, 0))) for m in months], unit=' KM'),
    })


@club_admin_required
@require_GET
def club_tours(request, club):
    """Sve ture društva (F23, F24, F27)."""
    tours = (Tour.objects.filter(club=club)
             .annotate(taken=Count('registrations', filter=Q(registrations__status=TourRegistration.Status.REGISTERED)),
                       waiting=Count('registrations', filter=Q(registrations__status=TourRegistration.Status.WAITLIST)),
                       guide_apps=Count('guide_assignments', filter=Q(guide_assignments__status=TourGuide.Status.APPLIED)))
             .order_by('-start_at'))
    now = timezone.now()
    return render(request, 'panel/club_tours.html', {
        'club': club, 'tab': 'tours',
        'upcoming': [t for t in tours if t.start_at >= now],
        'past': [t for t in tours if t.start_at < now][:20],
        'pending_members': ClubMembership.objects.filter(club=club, status=ClubMembership.Status.REQUESTED).count(),
        'guides_count': ClubGuide.objects.filter(club=club, is_active=True).count(),
    })


# --- F21 profil ---------------------------------------------------------------
@club_admin_required
@require_http_methods(['GET', 'POST'])
def club_profile(request, club):
    form = ClubProfileForm(request.POST or None, instance=club)
    if request.method == 'POST' and form.is_valid():
        form.save()
        audit(request, 'DRUSTVO_IZMJENA', 'club', club.pk)
        messages.success(request, 'Profil društva je sačuvan.')
        return redirect('panel:club', club_pk=club.pk)
    return render(request, 'panel/club_profile.html', {'club': club, 'form': form})


# --- F22 vodiči ---------------------------------------------------------------
@club_admin_required
@require_http_methods(['GET', 'POST'])
def guides(request, club):
    form = AddGuideForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.filter(email=form.cleaned_data['email'], is_active=True, is_system_admin=False).first()
        if user:
            g, created = ClubGuide.objects.get_or_create(club=club, user=user,
                                                         defaults={'license_number': form.cleaned_data['license_number']})
            if not created:
                g.is_active = True
                g.license_number = form.cleaned_data['license_number'] or g.license_number
                g.save(update_fields=['is_active', 'license_number'])
            audit(request, 'VODIC_DODAN', 'club_guide', g.pk, details=f'drustvo={club.pk}')
        # Ista poruka bez obzira da li nalog postoji (bez otkrivanja naloga).
        messages.info(request, 'Ako postoji aktivan nalog planinara sa tim emailom, dodan je kao vodič.')
        return redirect('panel:guides', club_pk=club.pk)
    items = ClubGuide.objects.filter(club=club, is_active=True).select_related('user').order_by('user__last_name')
    return render(request, 'panel/club_guides.html', {'club': club, 'form': form, 'items': items})


@club_admin_required
@require_POST
def guide_remove(request, club, pk):
    g = get_object_or_404(ClubGuide, club=club, pk=pk, is_active=True)
    g.is_active = False
    g.save(update_fields=['is_active'])
    audit(request, 'VODIC_UKLONJEN', 'club_guide', g.pk, details=f'drustvo={club.pk}')
    messages.success(request, f'{g.user.get_full_name()} više nije vodič društva.')
    return redirect('panel:guides', club_pk=club.pk)


# --- F23, F24 ture ------------------------------------------------------------
@club_admin_required
@require_http_methods(['GET', 'POST'])
def tour_create(request, club):
    form = TourForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        tour = form.save(commit=False)
        tour.club, tour.created_by, tour.status = club, request.user, Tour.Status.DRAFT
        tour.save()
        audit(request, 'TURA_KREIRANA', 'tour', tour.pk)
        messages.success(request, 'Tura je sačuvana kao nacrt. Objavite je kada bude spremna.')
        return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
    return render(request, 'panel/tour_form.html', {'club': club, 'form': form, 'tour': None})


@club_admin_required
@require_http_methods(['GET', 'POST'])
def tour_edit(request, club, pk):
    tour = club_tour(club, pk)
    if tour.status not in EDITABLE:
        messages.error(request, 'Održane i otkazane ture se ne mogu mijenjati.')
        return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
    form = TourForm(request.POST or None, instance=tour)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            locked = club_tour(club, pk, lock=True)
            if locked.status not in EDITABLE:
                messages.error(request, 'Tura je u međuvremenu promijenila status.')
                return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
            form.save()
        audit(request, 'TURA_IZMJENA', 'tour', tour.pk)
        messages.success(request, 'Tura je sačuvana.')
        return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
    return render(request, 'panel/tour_form.html', {'club': club, 'form': form, 'tour': tour})


TRANSITIONS = {
    # akcija: (dozvoljeni početni statusi, novi status, audit akcija, poruka)
    'publish': ([Tour.Status.DRAFT], Tour.Status.PUBLISHED, 'TURA_OBJAVLJENA', 'Tura je objavljena.'),
    'close': ([Tour.Status.PUBLISHED], Tour.Status.CLOSED, 'TURA_PRIJAVE_ZATVORENE', 'Prijave su zatvorene.'),
    'cancel': ([Tour.Status.PUBLISHED, Tour.Status.CLOSED], Tour.Status.CANCELLED, 'TURA_OTKAZANA', 'Tura je otkazana.'),
}


@club_admin_required
@require_POST
def tour_transition(request, club, pk, action):
    """F24 (objava, otkazivanje) i F18 (zatvaranje prijava)."""
    if action not in TRANSITIONS:
        raise Http404
    allowed, new, audit_action, msg = TRANSITIONS[action]
    with transaction.atomic():
        tour = club_tour(club, pk, lock=True)
        if tour.status not in allowed:
            messages.error(request, 'Ova promjena statusa nije dozvoljena.')
            return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
        if action == 'publish' and tour.registration_deadline <= timezone.now():
            messages.error(request, 'Rok prijave je prošao. Izmijenite turu prije objave.')
            return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
        tour.status = new
        tour.save(update_fields=['status', 'updated_at'])
    audit(request, audit_action, 'tour', tour.pk)
    messages.success(request, msg)
    return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)


@club_admin_required
@require_GET
def club_tour_detail(request, club, pk):
    """F25 (prijave vodiča) i F27 (prijave na turu: ime, prezime, status - BEZ ličnih podataka)."""
    tour = club_tour(club, pk)
    regs = (TourRegistration.objects.filter(tour=tour).select_related('user')
            .only('status', 'attendance', 'created_at', 'user__first_name', 'user__last_name')
            .order_by('status', 'created_at'))
    apps = TourGuide.objects.filter(tour=tour).select_related('user').order_by('status', 'created_at')
    approved_ids = [a.user_id for a in apps if a.status == TourGuide.Status.APPROVED]
    participant_ids = TourRegistration.objects.filter(tour=tour).exclude(
        status=TourRegistration.Status.CANCELLED).values_list('user_id', flat=True)
    assignable = (ClubGuide.objects.filter(club=club, is_active=True).exclude(user_id__in=approved_ids)
                  .exclude(user_id__in=participant_ids).select_related('user').order_by('user__last_name'))
    return render(request, 'panel/club_tour.html', {
        'club': club, 'tour': tour, 'regs': regs, 'apps': apps, 'editable': tour.status in EDITABLE,
        'assignable': assignable if tour.status in EDITABLE and tour.start_at > timezone.now() else [],
    })


# --- F25 odobravanje i dodjela vodiča ----------------------------------------
@club_admin_required
@require_POST
def guide_assign(request, club, pk):
    """Admin direktno dodjeljuje aktivnog vodiča SVOG društva turi (bez prijave vodiča)."""
    with transaction.atomic():
        tour = club_tour(club, pk, lock=True)
        if tour.status not in EDITABLE or tour.start_at <= timezone.now():
            messages.error(request, 'Vodič se može dodijeliti samo predstojećoj turi koja nije održana ni otkazana.')
            return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
        raw = request.POST.get('guide', '')
        guide = ClubGuide.objects.filter(club=club, is_active=True, pk=int(raw) if raw.isdigit() else -1).first()
        if guide is None:
            raise Http404
        if TourRegistration.objects.filter(tour=tour, user=guide.user).exclude(
                status=TourRegistration.Status.CANCELLED).exists():
            messages.error(request, 'Vodič je prijavljen kao učesnik ove ture.')
            return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
        tg, _ = TourGuide.objects.update_or_create(
            tour=tour, user=guide.user, defaults={'status': TourGuide.Status.APPROVED, 'decided_at': timezone.now()})
    audit(request, 'VODIC_DODIJELJEN', 'tour_guide', tg.pk, details=f'tura={tour.pk}')
    messages.success(request, f'{guide.user.get_full_name()} je dodijeljen kao vodič ture.')
    return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)


# --- F25 odobravanje vodiča ---------------------------------------------------
@club_admin_required
@require_POST
def guide_decide(request, club, pk, app_pk, decision):
    if decision not in ('approve', 'reject'):
        raise Http404
    tour = club_tour(club, pk)
    app = get_object_or_404(TourGuide, pk=app_pk, tour=tour, status=TourGuide.Status.APPLIED)
    if decision == 'approve':
        if not ClubGuide.objects.filter(club=club, user=app.user, is_active=True).exists():
            messages.error(request, 'Korisnik više nije aktivan vodič društva.')
            return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
        if TourRegistration.objects.filter(tour=tour, user=app.user).exclude(
                status=TourRegistration.Status.CANCELLED).exists():
            messages.error(request, 'Vodič je prijavljen kao učesnik ove ture.')
            return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
        app.status = TourGuide.Status.APPROVED
    else:
        app.status = TourGuide.Status.REJECTED
    app.decided_at = timezone.now()
    app.save(update_fields=['status', 'decided_at'])
    audit(request, 'VODIC_ODOBREN' if decision == 'approve' else 'VODIC_ODBIJEN', 'tour_guide', app.pk,
          details=f'tura={tour.pk}')
    messages.success(request, 'Odluka je sačuvana.')
    return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)


# --- F26, F28 članstva --------------------------------------------------------
@club_admin_required
@require_GET
def members(request, club):
    today = timezone.localdate()
    pending = ClubMembership.objects.filter(club=club, status=ClubMembership.Status.REQUESTED).select_related('user')
    active = (ClubMembership.objects.filter(club=club, status=ClubMembership.Status.APPROVED)
              .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
              .select_related('user').order_by('user__last_name'))
    return render(request, 'panel/club_members.html', {'club': club, 'pending': pending, 'active': active})


@club_admin_required
@require_POST
def membership_decide(request, club, pk, decision):
    if decision not in ('approve', 'reject'):
        raise Http404
    with transaction.atomic():
        m = get_object_or_404(ClubMembership.objects.select_for_update(), pk=pk, club=club,
                              status=ClubMembership.Status.REQUESTED)
        if decision == 'approve':
            m.status = ClubMembership.Status.APPROVED
            m.valid_until = date(timezone.localdate().year, 12, 31)    # članarina do kraja godine
        else:
            m.status = ClubMembership.Status.REJECTED
        m.decided_by, m.decided_at = request.user, timezone.now()
        m.save(update_fields=['status', 'valid_until', 'decided_by', 'decided_at'])
    audit(request, 'CLANSTVO_ODOBRENO' if decision == 'approve' else 'CLANSTVO_ODBIJENO', 'club_membership', m.pk)
    messages.success(request, 'Odluka je sačuvana.')
    return redirect('panel:members', club_pk=club.pk)
