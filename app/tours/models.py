from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from clubs.models import Club


MAX_ROUTE_POINTS = 500


def validate_route(value):
    """Ruta je lista tačaka [geografska širina, geografska dužina]. Strogo provjeravana jer se
    prikazuje u pregledniku: samo brojevi u ispravnom opsegu, bez ikakvog teksta."""
    if value in (None, []):
        return
    if not isinstance(value, list) or len(value) > MAX_ROUTE_POINTS:
        raise ValidationError(f'Ruta mora biti lista od najviše {MAX_ROUTE_POINTS} tačaka.')
    if len(value) == 1:
        raise ValidationError('Ruta mora imati najmanje dvije tačke.')
    for point in value:
        if (not isinstance(point, list) or len(point) != 2
                or not all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in point)):
            raise ValidationError('Svaka tačka rute mora biti par brojeva [širina, dužina].')
        lat, lng = point
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValidationError('Koordinate rute su izvan dozvoljenog opsega.')


class Tour(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'NACRT', 'Nacrt'
        PUBLISHED = 'OBJAVLJENA', 'Objavljena'
        CLOSED = 'PRIJAVE_ZATVORENE', 'Prijave zatvorene'
        DONE = 'ODRZANA', 'Održana'
        CANCELLED = 'OTKAZANA', 'Otkazana'

    class Difficulty(models.TextChoices):
        EASY = 'LAKA', 'Laka'
        MEDIUM = 'SREDNJA', 'Srednja'
        HARD = 'TESKA', 'Teška'
        VERY_HARD = 'VRLO_TESKA', 'Vrlo teška'

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name='tours')
    name = models.CharField('naziv', max_length=150)
    description = models.TextField('opis', max_length=4000, blank=True)
    region = models.CharField('regija', max_length=80, blank=True)
    start_at = models.DateTimeField('datum i vrijeme polaska')
    meeting_point = models.CharField('mjesto polaska', max_length=200)
    difficulty = models.CharField('težina', max_length=10, choices=Difficulty.choices)
    length_km = models.DecimalField('dužina (km)', max_digits=5, decimal_places=1,
                                    validators=[MinValueValidator(0), MaxValueValidator(500)])
    elevation_gain_m = models.PositiveIntegerField('visinska razlika (m)', validators=[MaxValueValidator(9000)])
    duration_h = models.DecimalField('trajanje (h)', max_digits=4, decimal_places=1,
                                     validators=[MinValueValidator(0), MaxValueValidator(240)])
    max_participants = models.PositiveSmallIntegerField('maks. broj učesnika',
                                                        validators=[MinValueValidator(1), MaxValueValidator(500)])
    price = models.DecimalField('cijena (KM)', max_digits=7, decimal_places=2, default=0,
                                validators=[MinValueValidator(0)])
    members_only = models.BooleanField('samo za članove', default=False)
    registration_deadline = models.DateTimeField('rok prijave')
    required_equipment = models.TextField('potrebna oprema', max_length=1000, blank=True)
    route = models.JSONField('ruta', default=list, blank=True, validators=[validate_route])
    status = models.CharField(max_length=17, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tours'
        ordering = ['start_at']
        constraints = [
            models.CheckConstraint(condition=Q(max_participants__gte=1), name='tour_max_participants_pos'),
            models.CheckConstraint(condition=Q(price__gte=0), name='tour_price_nonneg'),
            models.CheckConstraint(condition=Q(registration_deadline__lte=F('start_at')), name='tour_deadline_before_start'),
        ]

    def __str__(self):
        return self.name


class TourGuide(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'PRIJAVIO_SE', 'Prijavio se'
        APPROVED = 'ODOBREN', 'Odobren'
        REJECTED = 'ODBIJEN', 'Odbijen'

    tour = models.ForeignKey(Tour, on_delete=models.PROTECT, related_name='guide_assignments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='guide_assignments')
    status = models.CharField(max_length=11, choices=Status.choices, default=Status.APPLIED)
    created_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tour_guides'
        constraints = [models.UniqueConstraint(fields=['tour', 'user'], name='uniq_tour_guide')]


class TourRegistration(models.Model):
    class Status(models.TextChoices):
        REGISTERED = 'PRIJAVLJEN', 'Prijavljen'
        WAITLIST = 'NA_LISTI_CEKANJA', 'Na listi čekanja'
        CANCELLED = 'ODJAVLJEN', 'Odjavljen'

    class Attendance(models.TextChoices):
        PRESENT = 'PRISUSTVOVAO', 'Prisustvovao'
        ABSENT = 'NIJE_DOSAO', 'Nije došao'

    tour = models.ForeignKey(Tour, on_delete=models.PROTECT, related_name='registrations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tour_registrations')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REGISTERED)
    attendance = models.CharField(max_length=12, choices=Attendance.choices, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tour_registrations'
        ordering = ['created_at']
        constraints = [
            # korisnik može imati najviše jednu aktivnu prijavu na istu turu
            models.UniqueConstraint(fields=['tour', 'user'], condition=~Q(status='ODJAVLJEN'),
                                    name='uniq_active_registration'),
        ]


class TourReport(models.Model):
    tour = models.OneToOneField(Tour, on_delete=models.PROTECT, related_name='report')
    guide = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    text = models.TextField('izvještaj', max_length=4000)
    attendees_count = models.PositiveSmallIntegerField('broj prisutnih')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'tour_reports'
