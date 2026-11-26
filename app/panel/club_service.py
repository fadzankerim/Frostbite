"""Pravila admina društva (F18, F21-F28; politika 4.3 ograničenje 2).

Zajednička logika za HTML panel (views_club) i JSON API (api_club). Svaka funkcija dobija
`club` koji je već provjeren kroz admin_clubs(user), i svaki objekat se traži UNUTAR tog
društva - tuđe ture, vodiči i članstva daju 404 (Http404), isto kao nepostojeći.
Radnje koje nisu dozvoljene u trenutnom stanju bacaju ClubError sa porukom za korisnika.
"""
from datetime import date

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import User
from audit.log import audit
from clubs.models import ClubGuide, ClubMembership
from tours.models import Tour, TourGuide, TourRegistration

from .charts import MONTHS, last_months

EDITABLE = [Tour.Status.DRAFT, Tour.Status.PUBLISHED, Tour.Status.CLOSED]
ADD_GUIDE_MSG = 'Ako postoji aktivan nalog planinara sa tim emailom, dodan je kao vodič.'

TRANSITIONS = {
    # akcija: (dozvoljeni početni statusi, novi status, audit akcija, poruka)
    'publish': ([Tour.Status.DRAFT], Tour.Status.PUBLISHED, 'TURA_OBJAVLJENA', 'Tura je objavljena.'),
    'close': ([Tour.Status.PUBLISHED], Tour.Status.CLOSED, 'TURA_PRIJAVE_ZATVORENE', 'Prijave su zatvorene.'),
    'cancel': ([Tour.Status.PUBLISHED, Tour.Status.CLOSED], Tour.Status.CANCELLED, 'TURA_OTKAZANA', 'Tura je otkazana.'),
}


class ClubError(Exception):
    pass


def club_tour(club, pk, lock=False):
    qs = Tour.objects.filter(club=club)
    if lock:
        qs = qs.select_for_update()
    return get_object_or_404(qs, pk=pk)


def money(v):
    return round(float(v or 0), 2)


# --- pregled (analitika) ------------------------------------------------------
def dashboard(club):
    """Analitika društva: ture po fazama, prihod (procjena: cijena x prisutni / prijavljeni),
    popunjenost, vodiči, članovi i serije po mjesecima. Plaćanje se ne odvija kroz aplikaciju."""
    now = timezone.now()
    today = timezone.localdate()
    tours = Tour.objects.filter(club=club)
    present = Count('registrations', filter=Q(registrations__attendance=TourRegistration.Attendance.PRESENT))
    registered = Count('registrations', filter=Q(registrations__status=TourRegistration.Status.REGISTERED))
    has_guide = TourGuide.objects.filter(tour=OuterRef('pk'), status=TourGuide.Status.APPROVED)

    done = list(tours.filter(status=Tour.Status.DONE).annotate(present=present))
    active = list(tours.filter(status__in=[Tour.Status.PUBLISHED, Tour.Status.CLOSED], start_at__gte=now)
                  .annotate(taken=registered, guided=Exists(has_guide)).order_by('start_at'))

    months = last_months(today, 6)
    people, cash = {}, {}
    for t in done:
        local = timezone.localtime(t.start_at)
        key = (local.year, local.month)
        people[key] = people.get(key, 0) + t.present
        cash[key] = cash.get(key, 0) + money(t.price) * t.present

    guides = ClubGuide.objects.filter(club=club, is_active=True).select_related('user')
    led = dict(TourGuide.objects.filter(tour__club=club, status=TourGuide.Status.APPROVED, tour__status=Tour.Status.DONE)
               .values_list('user').annotate(c=Count('id')).values_list('user', 'c'))
    capacity = sum(t.max_participants for t in active)
    taken = sum(t.taken for t in active)
    return {
        'phases': {
            'draft': tours.filter(status=Tour.Status.DRAFT).count(),
            'active': len(active),
            'done': len(done),
            'cancelled': tours.filter(status=Tour.Status.CANCELLED).count(),
        },
        'money': {'earned': sum(money(t.price) * t.present for t in done),
                  'expected': sum(money(t.price) * t.taken for t in active)},
        'fill': {'taken': taken, 'capacity': capacity, 'pct': round(100 * taken / capacity) if capacity else 0},
        'active': active,
        'unguided': [t for t in active if not t.guided],
        'guide_rows': sorted(((g.user.get_full_name(), led.get(g.user_id, 0)) for g in guides), key=lambda r: -r[1]),
        'members_count': ClubMembership.objects.filter(club=club, status=ClubMembership.Status.APPROVED)
                         .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).count(),
        'pending_members': ClubMembership.objects.filter(club=club, status=ClubMembership.Status.REQUESTED).count(),
        'pending_guides': TourGuide.objects.filter(tour__club=club, status=TourGuide.Status.APPLIED, tour__start_at__gte=now).count(),
        'months': [(f'{MONTHS[m - 1]} {str(y)[2:]}', people.get((y, m), 0), round(cash.get((y, m), 0)))
                   for y, m in months],
    }


def tours_overview(club):
    """Sve ture društva sa brojem prijavljenih, liste čekanja i prijava vodiča (F23, F24, F27)."""
    tours = (Tour.objects.filter(club=club)
             .annotate(taken=Count('registrations', filter=Q(registrations__status=TourRegistration.Status.REGISTERED)),
                       waiting=Count('registrations', filter=Q(registrations__status=TourRegistration.Status.WAITLIST)),
                       guide_apps=Count('guide_assignments', filter=Q(guide_assignments__status=TourGuide.Status.APPLIED)))
             .order_by('-start_at'))
    now = timezone.now()
    return [t for t in tours if t.start_at >= now], [t for t in tours if t.start_at < now][:20]


# --- F21 profil ----------------------------------------------------------------
def save_profile(request, club, form):
    form.save()
    audit(request, 'DRUSTVO_IZMJENA', 'club', club.pk)


# --- F22 vodiči društva ------------------------------------------------------------
def club_guides(club):
    return ClubGuide.objects.filter(club=club, is_active=True).select_related('user').order_by('user__last_name')


def add_guide(request, club, email, license_number):
    """Dodaje aktivnog planinara kao vodiča. Pozivalac uvijek prikazuje ADD_GUIDE_MSG
    (isti ishod bez obzira da li nalog postoji - bez otkrivanja naloga)."""
    user = User.objects.filter(email=email, is_active=True, is_system_admin=False).first()
    if not user:
        return
    g, created = ClubGuide.objects.get_or_create(club=club, user=user, defaults={'license_number': license_number})
    if not created:
        g.is_active = True
        g.license_number = license_number or g.license_number
        g.save(update_fields=['is_active', 'license_number'])
    audit(request, 'VODIC_DODAN', 'club_guide', g.pk, details=f'drustvo={club.pk}')


def remove_guide(request, club, pk):
    g = get_object_or_404(ClubGuide, club=club, pk=pk, is_active=True)
    g.is_active = False
    g.save(update_fields=['is_active'])
    audit(request, 'VODIC_UKLONJEN', 'club_guide', g.pk, details=f'drustvo={club.pk}')
    return g


# --- F23, F24 ture -------------------------------------------------------------------
def create_tour(request, club, form):
    tour = form.save(commit=False)
    tour.club, tour.created_by, tour.status = club, request.user, Tour.Status.DRAFT
    tour.save()
    audit(request, 'TURA_KREIRANA', 'tour', tour.pk)
    return tour


def ensure_editable(tour):
    if tour.status not in EDITABLE:
        raise ClubError('Održane i otkazane ture se ne mogu mijenjati.')


def edit_tour(request, club, pk, form):
    with transaction.atomic():
        locked = club_tour(club, pk, lock=True)
        if locked.status not in EDITABLE:
            raise ClubError('Tura je u međuvremenu promijenila status.')
        form.save()
    audit(request, 'TURA_IZMJENA', 'tour', pk)


def transition(request, club, pk, action):
    """F24 (objava, otkazivanje) i F18 (zatvaranje prijava). Nepoznata akcija = 404."""
    if action not in TRANSITIONS:
        raise Http404
    allowed, new, audit_action, msg = TRANSITIONS[action]
    with transaction.atomic():
        tour = club_tour(club, pk, lock=True)
        if tour.status not in allowed:
            raise ClubError('Ova promjena statusa nije dozvoljena.')
        if action == 'publish' and tour.registration_deadline <= timezone.now():
            raise ClubError('Rok prijave je prošao. Izmijenite turu prije objave.')
        tour.status = new
        tour.save(update_fields=['status', 'updated_at'])
    audit(request, audit_action, 'tour', tour.pk)
    return msg


def available_transitions(tour):
    return [a for a, (allowed, *_rest) in TRANSITIONS.items() if tour.status in allowed]


def tour_detail(club, pk):
    """F25 (prijave vodiča) i F27 (prijave na turu: ime, prezime, status - BEZ ličnih podataka)."""
    tour = club_tour(club, pk)
    regs = (TourRegistration.objects.filter(tour=tour).select_related('user')
            .only('status', 'attendance', 'created_at', 'user__first_name', 'user__last_name')
            .order_by('status', 'created_at'))
    apps = TourGuide.objects.filter(tour=tour).select_related('user').order_by('status', 'created_at')
    approved_ids = [a.user_id for a in apps if a.status == TourGuide.Status.APPROVED]
    participant_ids = TourRegistration.objects.filter(tour=tour).exclude(
        status=TourRegistration.Status.CANCELLED).values_list('user_id', flat=True)
    assignable = []
    if tour.status in EDITABLE and tour.start_at > timezone.now():
        assignable = (ClubGuide.objects.filter(club=club, is_active=True).exclude(user_id__in=approved_ids)
                      .exclude(user_id__in=participant_ids).select_related('user').order_by('user__last_name'))
    return tour, regs, apps, assignable


# --- F25 vodiči na turi ----------------------------------------------------------------
def assign_guide(request, club, pk, guide_pk):
    """Admin direktno dodjeljuje aktivnog vodiča SVOG društva turi (bez prijave vodiča)."""
    with transaction.atomic():
        tour = club_tour(club, pk, lock=True)
        if tour.status not in EDITABLE or tour.start_at <= timezone.now():
            raise ClubError('Vodič se može dodijeliti samo predstojećoj turi koja nije održana ni otkazana.')
        guide = ClubGuide.objects.filter(club=club, is_active=True, pk=guide_pk).first()
        if guide is None:
            raise Http404
        if TourRegistration.objects.filter(tour=tour, user=guide.user).exclude(
                status=TourRegistration.Status.CANCELLED).exists():
            raise ClubError('Vodič je prijavljen kao učesnik ove ture.')
        tg, _ = TourGuide.objects.update_or_create(
            tour=tour, user=guide.user, defaults={'status': TourGuide.Status.APPROVED, 'decided_at': timezone.now()})
    audit(request, 'VODIC_DODIJELJEN', 'tour_guide', tg.pk, details=f'tura={tour.pk}')
    return f'{guide.user.get_full_name()} je dodijeljen kao vodič ture.'


def decide_guide(request, club, pk, app_pk, decision):
    if decision not in ('approve', 'reject'):
        raise Http404
    tour = club_tour(club, pk)
    app = get_object_or_404(TourGuide, pk=app_pk, tour=tour, status=TourGuide.Status.APPLIED)
    if decision == 'approve':
        if not ClubGuide.objects.filter(club=club, user=app.user, is_active=True).exists():
            raise ClubError('Korisnik više nije aktivan vodič društva.')
        if TourRegistration.objects.filter(tour=tour, user=app.user).exclude(
                status=TourRegistration.Status.CANCELLED).exists():
            raise ClubError('Vodič je prijavljen kao učesnik ove ture.')
        app.status = TourGuide.Status.APPROVED
    else:
        app.status = TourGuide.Status.REJECTED
    app.decided_at = timezone.now()
    app.save(update_fields=['status', 'decided_at'])
    audit(request, 'VODIC_ODOBREN' if decision == 'approve' else 'VODIC_ODBIJEN', 'tour_guide', app.pk,
          details=f'tura={tour.pk}')


# --- F26, F28 članstva -------------------------------------------------------------------
def members(club):
    today = timezone.localdate()
    pending = ClubMembership.objects.filter(club=club, status=ClubMembership.Status.REQUESTED).select_related('user')
    active = (ClubMembership.objects.filter(club=club, status=ClubMembership.Status.APPROVED)
              .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
              .select_related('user').order_by('user__last_name'))
    return pending, active


def decide_membership(request, club, pk, decision):
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
    return m
