"""Zajednički podaci za testove panela: dva društva (A, B), admini, vodiči, planinar sa ličnim podacima."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from clubs.models import Club, ClubAdmin, ClubGuide
from tours.models import Tour, TourGuide, TourRegistration

PW = 'Snijeg-Na-Bjelasnici-42'


class Base(TestCase):
    def setUp(self):
        mk = lambda e, f, **kw: User.objects.create_user(e, PW, first_name=f, last_name='Test', **kw)  # noqa: E731
        self.adminA, self.adminB = mk('a@a.ba', 'AdminA'), mk('b@b.ba', 'AdminB')
        self.guideA, self.guideA2 = mk('g@a.ba', 'VodicA'), mk('g2@a.ba', 'VodicA2')
        self.hiker = mk('h@p.ba', 'Planinar', phone='061 999 888', health_notes='TAJNA-DIJAGNOZA',
                        emergency_contact_name='Mama', emergency_contact_phone='062 777 666')
        self.sys = User.objects.create_system_admin('s@f.ba', PW, first_name='Sys', last_name='Admin')
        self.A = Club.objects.create(name='PD A', city='X', status=Club.Status.APPROVED, created_by=self.adminA)
        self.B = Club.objects.create(name='PD B', city='Y', status=Club.Status.APPROVED, created_by=self.adminB)
        ClubAdmin.objects.create(club=self.A, user=self.adminA)
        ClubAdmin.objects.create(club=self.B, user=self.adminB)
        ClubGuide.objects.create(club=self.A, user=self.guideA)
        ClubGuide.objects.create(club=self.A, user=self.guideA2)
        self.tA = self.tour(self.A)
        self.tB = self.tour(self.B)
        TourGuide.objects.create(tour=self.tA, user=self.guideA, status=TourGuide.Status.APPROVED)
        self.reg = TourRegistration.objects.create(tour=self.tA, user=self.hiker)

    def tour(self, club, days=5, **kw):
        now = timezone.now()
        data = dict(club=club, name=f'Tura {club.name}', start_at=now + timedelta(days=days),
                    registration_deadline=now + timedelta(days=days - 1), meeting_point='M',
                    difficulty=Tour.Difficulty.EASY, length_km=5, elevation_gain_m=100, duration_h=2,
                    max_participants=10, status=Tour.Status.PUBLISHED, created_by=club.created_by)
        data.update(kw)
        return Tour.objects.create(**data)

    def as_(self, user):
        self.client.force_login(user)
