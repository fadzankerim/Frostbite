"""Pravila za vodiče (F15-F20; politika 4.3 ograničenja 1 i 2, politika 4.5).

Zajednička logika za HTML panel (views_guide) i JSON API (api_guide): jedno mjesto za
pravila, transakcije i audit. Funkcije bacaju Http404 za ture koje korisnik ne smije vidjeti
(isto kao nepostojeće) i GuideError za radnje koje nisu dozvoljene u trenutnom stanju.
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.permissions import guide_clubs
from audit.log import audit
from tours.models import Tour, TourGuide, TourRegistration, TourReport

from .forms import ReportForm

PERSONAL_DATA_DAYS_AFTER = 7       # ograničenje 1: lični podaci do 7 dana nakon ture
ATTENDANCE_HOURS_BEFORE = 12       # prisustvo i izvještaj od 12 sati prije polaska
OPEN_STATUSES = [Tour.Status.DRAFT, Tour.Status.PUBLISHED, Tour.Status.CLOSED]


class GuideError(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or {}


def led_tours(user):
    """Ture na kojima je korisnik ODOBREN vodič, u društvima u kojima je aktivan vodič."""
    return Tour.objects.filter(
        guide_assignments__user=user, guide_assignments__status=TourGuide.Status.APPROVED,
        club__in=guide_clubs(user),
    ).select_related('club').distinct()


def get_led_tour(user, pk, lock=False):
    """Tura koju korisnik vodi, unutar vremenskog prozora za lične podatke - inače 404."""
    qs = led_tours(user).exclude(status=Tour.Status.CANCELLED)
    tour = get_object_or_404(qs, pk=pk)
    if timezone.now() > tour.start_at + timedelta(days=PERSONAL_DATA_DAYS_AFTER):
        raise Http404
    if lock:
        tour = Tour.objects.select_for_update().get(pk=tour.pk)
    return tour


def attendance_open(tour):
    return tour.start_at - timedelta(hours=ATTENDANCE_HOURS_BEFORE) <= timezone.now()


def open_tours(user):
    """F15 - buduće ture vlastitih društava bez odobrenog vodiča (sa oznakom da li se korisnik prijavio)."""
    has_approved = TourGuide.objects.filter(tour=OuterRef('pk'), status=TourGuide.Status.APPROVED)
    my_app = TourGuide.objects.filter(tour=OuterRef('pk'), user=user)
    return (Tour.objects
            .filter(club__in=guide_clubs(user), start_at__gt=timezone.now(), status__in=OPEN_STATUSES)
            .annotate(has_guide=Exists(has_approved), applied=Exists(my_app))
            .filter(has_guide=False).select_related('club').order_by('start_at'))


def my_tours(user):
    """Ture koje korisnik vodi, dok traje pristup ličnim podacima."""
    since = timezone.now() - timedelta(days=PERSONAL_DATA_DAYS_AFTER)
    return led_tours(user).filter(start_at__gte=since).order_by('start_at')


def apply(request, pk):
    """F16 - prijava za vođenje ture vlastitog društva."""
    tour = get_object_or_404(
        Tour.objects.filter(club__in=guide_clubs(request.user), start_at__gt=timezone.now(), status__in=OPEN_STATUSES),
        pk=pk)
    if TourRegistration.objects.filter(tour=tour, user=request.user,
                                       status__in=[TourRegistration.Status.REGISTERED, TourRegistration.Status.WAITLIST]).exists():
        raise GuideError('Prijavljeni ste kao učesnik ove ture. Prvo se odjavite.')
    try:
        with transaction.atomic():
            tg = TourGuide.objects.create(tour=tour, user=request.user)
    except IntegrityError:
        raise GuideError('Već ste se prijavili za vođenje ove ture.')
    audit(request, 'VODIC_PRIJAVA', 'tour_guide', tg.pk, details=f'tura={tour.pk}')
    return tg


def participants(request, pk):
    """F17 - učesnici sa ličnim podacima (samo odobreni vodič, ograničenje 1). Svaki pristup se bilježi."""
    tour = get_led_tour(request.user, pk)
    regs = list(TourRegistration.objects.filter(tour=tour)
                .exclude(status=TourRegistration.Status.CANCELLED)
                .select_related('user').order_by('status', 'created_at'))
    audit(request, 'PRISTUP_LICNIM_PODACIMA', 'tour', tour.pk, details=f'broj={len(regs)}')
    return tour, regs, TourReport.objects.filter(tour=tour).first()


def close_registrations(request, pk):
    """F18 - zatvaranje prijava (OBJAVLJENA -> PRIJAVE ZATVORENE)."""
    with transaction.atomic():
        tour = get_led_tour(request.user, pk, lock=True)
        if tour.status != Tour.Status.PUBLISHED:
            raise GuideError('Prijave se mogu zatvoriti samo na objavljenoj turi.')
        tour.status = Tour.Status.CLOSED
        tour.save(update_fields=['status', 'updated_at'])
    audit(request, 'TURA_PRIJAVE_ZATVORENE', 'tour', tour.pk)
    return tour


def save_attendance(request, pk, present_ids):
    """F19 - prisustvo za sve prijavljene; ko nije označen, nije došao. Vraća broj prisutnih."""
    with transaction.atomic():
        tour = get_led_tour(request.user, pk, lock=True)
        if tour.status not in (Tour.Status.PUBLISHED, Tour.Status.CLOSED) or not attendance_open(tour):
            raise GuideError('Prisustvo se evidentira na dan ture.')
        regs = list(TourRegistration.objects.filter(tour=tour, status=TourRegistration.Status.REGISTERED))
        for r in regs:
            r.attendance = (TourRegistration.Attendance.PRESENT if r.pk in present_ids
                            else TourRegistration.Attendance.ABSENT)
            r.save(update_fields=['attendance', 'updated_at'])
    count = len(present_ids & {r.pk for r in regs})
    audit(request, 'TURA_PRISUSTVO', 'tour', tour.pk, details=f'prisutno={count}')
    return count


def save_report(request, pk, data):
    """F20 - izvještaj sa ture; tura prelazi u status ODRŽANA."""
    with transaction.atomic():
        tour = get_led_tour(request.user, pk, lock=True)
        if TourReport.objects.filter(tour=tour).exists() or not attendance_open(tour) \
                or tour.status not in (Tour.Status.PUBLISHED, Tour.Status.CLOSED):
            raise GuideError('Izvještaj se ne može unijeti za ovu turu.')
        form = ReportForm(data)
        if not form.is_valid():
            raise GuideError('Izvještaj nije ispravan.', form.errors.get_json_data())
        rep = form.save(commit=False)
        rep.tour, rep.guide = tour, request.user
        rep.attendees_count = TourRegistration.objects.filter(
            tour=tour, attendance=TourRegistration.Attendance.PRESENT).count()
        rep.save()
        tour.status = Tour.Status.DONE
        tour.save(update_fields=['status', 'updated_at'])
    audit(request, 'TURA_IZVJESTAJ', 'tour', tour.pk)
    return rep
