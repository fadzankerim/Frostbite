"""Funkcionalnosti vodiča (F15-F20), politika 4.3 ograničenja 1 i 2, politika 4.5."""
from datetime import timedelta

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.permissions import guide_clubs, guide_required
from audit.log import audit
from tours.models import Tour, TourGuide, TourRegistration, TourReport

from .forms import ReportForm

PERSONAL_DATA_DAYS_AFTER = 7       # ograničenje 1: lični podaci do 7 dana nakon ture


def led_tours(user):
    """Ture na kojima je korisnik ODOBREN vodič, u društvima u kojima je aktivan vodič."""
    return Tour.objects.filter(
        guide_assignments__user=user, guide_assignments__status=TourGuide.Status.APPROVED,
        club__in=guide_clubs(user),
    ).select_related('club').distinct()


def get_led_tour(request, pk, lock=False):
    """Tura koju korisnik vodi, unutar vremenskog prozora za lične podatke - inače 404."""
    qs = led_tours(request.user).exclude(status=Tour.Status.CANCELLED)
    tour = get_object_or_404(qs, pk=pk)
    if timezone.now() > tour.start_at + timedelta(days=PERSONAL_DATA_DAYS_AFTER):
        raise Http404
    if lock:
        tour = Tour.objects.select_for_update().get(pk=tour.pk)
    return tour


@guide_required
@require_GET
def dashboard(request):
    """F15 - ture vlastitih društava bez vodiča + ture koje korisnik vodi."""
    now = timezone.now()
    has_approved = TourGuide.objects.filter(tour=OuterRef('pk'), status=TourGuide.Status.APPROVED)
    my_app = TourGuide.objects.filter(tour=OuterRef('pk'), user=request.user)
    open_tours = (Tour.objects
                  .filter(club__in=guide_clubs(request.user), start_at__gt=now,
                          status__in=[Tour.Status.DRAFT, Tour.Status.PUBLISHED, Tour.Status.CLOSED])
                  .annotate(has_guide=Exists(has_approved), applied=Exists(my_app))
                  .filter(has_guide=False).select_related('club').order_by('start_at'))
    mine = led_tours(request.user).filter(start_at__gte=now - timedelta(days=PERSONAL_DATA_DAYS_AFTER)).order_by('start_at')
    return render(request, 'panel/guide_dashboard.html', {'open_tours': open_tours, 'mine': mine})


@guide_required
@require_POST
def apply(request, pk):
    """F16 - prijava za vođenje ture vlastitog društva."""
    tour = get_object_or_404(
        Tour.objects.filter(club__in=guide_clubs(request.user), start_at__gt=timezone.now(),
                            status__in=[Tour.Status.DRAFT, Tour.Status.PUBLISHED, Tour.Status.CLOSED]), pk=pk)
    if TourRegistration.objects.filter(tour=tour, user=request.user,
                                       status__in=[TourRegistration.Status.REGISTERED, TourRegistration.Status.WAITLIST]).exists():
        messages.error(request, 'Prijavljeni ste kao učesnik ove ture. Prvo se odjavite.')
        return redirect('panel:guide')
    try:
        with transaction.atomic():
            tg = TourGuide.objects.create(tour=tour, user=request.user)
        audit(request, 'VODIC_PRIJAVA', 'tour_guide', tg.pk, details=f'tura={tour.pk}')
        messages.success(request, 'Prijava za vođenje je poslana adminu društva.')
    except IntegrityError:
        messages.error(request, 'Već ste se prijavili za vođenje ove ture.')
    return redirect('panel:guide')


@guide_required
@require_GET
def tour_participants(request, pk):
    """F17 - učesnici ture sa ličnim podacima (samo odobreni vodič, ograničenje 1)."""
    tour = get_led_tour(request, pk)
    regs = (TourRegistration.objects.filter(tour=tour)
            .exclude(status=TourRegistration.Status.CANCELLED)
            .select_related('user').order_by('status', 'created_at'))
    audit(request, 'PRISTUP_LICNIM_PODACIMA', 'tour', tour.pk, details=f'broj={len(regs)}')
    can_attend = tour.start_at - timedelta(hours=12) <= timezone.now()
    report = TourReport.objects.filter(tour=tour).first()
    from tours.views import start_point
    return render(request, 'panel/guide_tour.html', {
        'tour': tour, 'regs': regs, 'can_attend': can_attend, 'report': report, 'start': start_point(tour),
        'report_form': ReportForm() if can_attend and not report else None,
    })


@guide_required
@require_POST
def close_registrations(request, pk):
    """F18 - zatvaranje prijava (OBJAVLJENA -> PRIJAVE ZATVORENE)."""
    with transaction.atomic():
        tour = get_led_tour(request, pk, lock=True)
        if tour.status != Tour.Status.PUBLISHED:
            messages.error(request, 'Prijave se mogu zatvoriti samo na objavljenoj turi.')
            return redirect('panel:guide_tour', pk=tour.pk)
        tour.status = Tour.Status.CLOSED
        tour.save(update_fields=['status', 'updated_at'])
    audit(request, 'TURA_PRIJAVE_ZATVORENE', 'tour', tour.pk)
    messages.success(request, 'Prijave su zatvorene.')
    return redirect('panel:guide_tour', pk=tour.pk)


@guide_required
@require_POST
def attendance(request, pk):
    """F19 - evidencija prisustva (od 12 sati prije polaska)."""
    with transaction.atomic():
        tour = get_led_tour(request, pk, lock=True)
        if tour.status not in (Tour.Status.PUBLISHED, Tour.Status.CLOSED) \
                or timezone.now() < tour.start_at - timedelta(hours=12):
            messages.error(request, 'Prisustvo se evidentira na dan ture.')
            return redirect('panel:guide_tour', pk=tour.pk)
        regs = TourRegistration.objects.filter(tour=tour, status=TourRegistration.Status.REGISTERED)
        present = set()
        for raw in request.POST.getlist('present'):
            if raw.isdigit():
                present.add(int(raw))
        for r in regs:
            r.attendance = (TourRegistration.Attendance.PRESENT if r.pk in present
                            else TourRegistration.Attendance.ABSENT)
            r.save(update_fields=['attendance', 'updated_at'])
    audit(request, 'TURA_PRISUSTVO', 'tour', tour.pk, details=f'prisutno={len(present & {r.pk for r in regs})}')
    messages.success(request, 'Prisustvo je sačuvano.')
    return redirect('panel:guide_tour', pk=tour.pk)


@guide_required
@require_http_methods(['POST'])
def report(request, pk):
    """F20 - izvještaj sa ture; tura prelazi u status ODRŽANA."""
    with transaction.atomic():
        tour = get_led_tour(request, pk, lock=True)
        if TourReport.objects.filter(tour=tour).exists() or timezone.now() < tour.start_at - timedelta(hours=12) \
                or tour.status not in (Tour.Status.PUBLISHED, Tour.Status.CLOSED):
            messages.error(request, 'Izvještaj se ne može unijeti za ovu turu.')
            return redirect('panel:guide_tour', pk=tour.pk)
        form = ReportForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Izvještaj nije ispravan.')
            return redirect('panel:guide_tour', pk=tour.pk)
        rep = form.save(commit=False)
        rep.tour, rep.guide = tour, request.user
        rep.attendees_count = TourRegistration.objects.filter(
            tour=tour, attendance=TourRegistration.Attendance.PRESENT).count()
        rep.save()
        tour.status = Tour.Status.DONE
        tour.save(update_fields=['status', 'updated_at'])
    audit(request, 'TURA_IZVJESTAJ', 'tour', tour.pk)
    messages.success(request, 'Izvještaj je sačuvan, a tura je označena kao održana.')
    return redirect('panel:guide_tour', pk=tour.pk)
