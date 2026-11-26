"""Bedževi: pravila (pozitivan i negativan slučaj), idempotentnost, otpornost glavne radnje,
privatnost (/api/me/badges/ samo vlastiti) i katalog samo za čitanje."""
import json
from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from clubs.models import Club, ClubAdmin, ClubMembership
from panel.test_base import Base
from tours.models import Tour, TourGuide, TourRegistration, TourReport

from . import services
from .models import Badge, UserBadge

PRESENT = TourRegistration.Attendance.PRESENT


def codes(user):
    return set(UserBadge.objects.filter(user=user).values_list('badge__code', flat=True))


class BadgeBase(Base):
    def setUp(self):
        super().setUp()
        self.c = Client(enforce_csrf_checks=True)

    def login(self, user):
        self.c.force_login(user)
        self.c.get(reverse('api_auth:csrf'))
        self.token = self.c.cookies['csrftoken'].value

    def post(self, name, *args, data=None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.c.post(reverse(name, args=args), json.dumps(data or {}), content_type='application/json',
                               headers={'X-CSRFToken': self.token})

    def attended(self, user, n, **tour_kw):
        for i in range(n):
            t = self.tour(self.A, days=-10 - i, registration_deadline=timezone.now() - timedelta(days=11 + i),
                          status=Tour.Status.DONE, **tour_kw)
            TourRegistration.objects.create(tour=t, user=user, attendance=PRESENT)


class CatalogTests(BadgeBase):
    def test_catalog_is_public_and_read_only(self):
        r = self.c.get(reverse('api_badges:catalog'))
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(len(d['results']), Badge.objects.count())
        self.assertEqual(set(d['results'][0]), {'code', 'name', 'description', 'role', 'tier', 'icon'})
        self.login(self.sys)
        for m in ('post', 'put', 'patch', 'delete'):
            r = getattr(self.c, m)(reverse('api_badges:catalog'), '{}', content_type='application/json',
                                   headers={'X-CSRFToken': self.token})
            self.assertEqual(r.status_code, 405, m)

    def test_every_rule_has_catalog_entry(self):
        from .rules import RULES
        self.assertEqual({r.code for r in RULES}, set(Badge.objects.values_list('code', flat=True)))


class HikerRuleTests(BadgeBase):
    def test_first_step_on_register_via_api(self):
        t = self.tour(self.A)
        self.login(self.hiker)
        self.assertEqual(self.post('api_tours:register', t.pk).status_code, 201)
        self.assertIn('prvi-korak', codes(self.hiker))
        self.assertTrue(AuditLog.objects.filter(action='BEDZ_DODIJELJEN', user=self.hiker).exists())

    def test_cancelled_registration_does_not_count(self):
        self.reg.status = TourRegistration.Status.CANCELLED
        self.reg.save()
        services.evaluate(self.hiker)
        self.assertNotIn('prvi-korak', codes(self.hiker))

    def test_registration_without_attendance_gives_no_peak(self):
        TourRegistration.objects.filter(pk=self.reg.pk).update(attendance=TourRegistration.Attendance.ABSENT)
        services.evaluate(self.hiker)
        self.assertEqual(codes(self.hiker), {'prvi-korak'})

    def test_attendance_via_guide_api(self):
        Tour.objects.filter(pk=self.tA.pk).update(start_at=timezone.now() - timedelta(hours=2),
                                                  registration_deadline=timezone.now() - timedelta(days=1),
                                                  status=Tour.Status.CLOSED)
        self.login(self.guideA)
        self.assertEqual(self.post('api_guide:attendance', self.tA.pk, data={'present': [self.reg.pk]}).status_code, 200)
        self.assertIn('prvi-vrh', codes(self.hiker))
        self.assertEqual(self.post('api_guide:report', self.tA.pk, data={'text': 'Sve u redu.'}).status_code, 201)
        self.assertIn('prvi-put-na-celu', codes(self.guideA))

    def test_counts_and_elevation(self):
        self.attended(self.hiker, 4, elevation_gain_m=1200)
        services.evaluate(self.hiker)
        self.assertNotIn('planinar-5', codes(self.hiker))
        self.assertNotIn('visinac-5000', codes(self.hiker))
        self.attended(self.hiker, 1, elevation_gain_m=300)
        services.evaluate(self.hiker)
        self.assertTrue({'prvi-vrh', 'planinar-5', 'visinac-5000'} <= codes(self.hiker))
        self.assertNotIn('planinar-10', codes(self.hiker))

    def test_versatile_needs_all_difficulties(self):
        diffs = [d for d, _ in Tour.Difficulty.choices]
        for d in diffs[:-1]:
            self.attended(self.hiker, 1, difficulty=d)
        services.evaluate(self.hiker)
        self.assertNotIn('svestrani', codes(self.hiker))
        self.attended(self.hiker, 1, difficulty=diffs[-1])
        services.evaluate(self.hiker)
        self.assertIn('svestrani', codes(self.hiker))

    def test_membership(self):
        m = ClubMembership.objects.create(club=self.A, user=self.hiker)
        services.evaluate(self.hiker)
        self.assertNotIn('clan-drustva', codes(self.hiker))
        self.login(self.adminA)
        self.assertEqual(self.post('api_manage:member_decide', self.A.pk, m.pk, data={'decision': 'approve'}).status_code, 200)
        self.assertIn('clan-drustva', codes(self.hiker))


class GuideRuleTests(BadgeBase):
    def test_led_tours_and_reports(self):
        services.evaluate(self.guideA)
        self.assertFalse(codes(self.guideA) & {'prvi-put-na-celu', 'iskusni-vodic-5'})
        for i in range(10):
            t = self.tour(self.A, days=-3 - i, registration_deadline=timezone.now() - timedelta(days=4 + i),
                          status=Tour.Status.DONE)
            TourGuide.objects.create(tour=t, user=self.guideA, status=TourGuide.Status.APPROVED)
            TourReport.objects.create(tour=t, guide=self.guideA, text='x', attendees_count=0)
        # neodobren vodič se ne broji
        t = self.tour(self.A, days=-1, registration_deadline=timezone.now() - timedelta(days=2), status=Tour.Status.DONE)
        TourGuide.objects.create(tour=t, user=self.guideA2, status=TourGuide.Status.REJECTED)
        services.evaluate(self.guideA)
        services.evaluate(self.guideA2)
        self.assertTrue({'prvi-put-na-celu', 'iskusni-vodic-5', 'uredan-dnevnik'} <= codes(self.guideA))
        self.assertNotIn('iskusni-vodic-20', codes(self.guideA))
        self.assertEqual(codes(self.guideA2), set())


class ClubAdminRuleTests(BadgeBase):
    def test_founder_and_guardian_on_club_decision(self):
        founder = self.guideA2
        club = Club.objects.create(name='PD Novo', city='Z', created_by=founder)
        ClubAdmin.objects.create(club=club, user=founder)
        services.evaluate(founder)
        self.assertNotIn('osnivac', codes(founder))
        self.login(self.sys)
        self.assertEqual(self.post('api_system:club_decide', club.pk, data={'action': 'approve'}).status_code, 200)
        self.assertIn('osnivac', codes(founder))
        self.assertEqual(codes(self.sys), {'cuvar-planine'})

    def test_system_admin_gets_no_hiker_badges(self):
        TourRegistration.objects.create(tour=self.tB, user=self.sys)
        services.evaluate(self.sys)
        self.assertEqual(codes(self.sys), set())

    def test_first_publish(self):
        draft = self.tour(self.A, status=Tour.Status.DRAFT)
        Tour.objects.filter(club=self.A).exclude(pk=draft.pk).update(status=Tour.Status.DRAFT)
        services.evaluate(self.adminA)
        self.assertNotIn('prva-objava', codes(self.adminA))
        self.login(self.adminA)
        self.assertEqual(self.post('api_manage:transition', self.A.pk, draft.pk, data={'action': 'publish'}).status_code, 200)
        self.assertIn('prva-objava', codes(self.adminA))
        self.assertNotIn('prva-objava', codes(self.adminB))

    def test_full_house(self):
        t = self.tour(self.A, max_participants=1)
        services.evaluate(self.adminA)
        self.assertNotIn('puna-kuca', codes(self.adminA))
        self.login(self.guideA2)
        self.assertEqual(self.post('api_tours:register', t.pk).status_code, 201)
        self.assertIn('puna-kuca', codes(self.adminA))
        self.assertNotIn('puna-kuca', codes(self.adminB))

    def test_hundred_hikers(self):
        t = self.tour(self.A, max_participants=200)
        from accounts.models import User
        users = [User.objects.create_user(f'u{i}@p.ba', 'x', first_name='U', last_name='U') for i in range(100)]
        TourRegistration.objects.bulk_create(
            [TourRegistration(tour=t, user=u, attendance=PRESENT) for u in users[:99]])
        services.evaluate(self.adminA)
        self.assertNotIn('sto-planinara', codes(self.adminA))
        TourRegistration.objects.create(tour=t, user=users[99], attendance=PRESENT)
        services.evaluate(self.adminA)
        self.assertIn('sto-planinara', codes(self.adminA))


class ServiceTests(BadgeBase):
    def test_idempotent(self):
        self.assertEqual(len(services.evaluate(self.hiker)), 1)
        self.assertEqual(services.evaluate(self.hiker), [])
        services.evaluate_safely([self.hiker], ['registration'])
        self.assertEqual(UserBadge.objects.filter(user=self.hiker).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='BEDZ_DODIJELJEN').count(), 1)

    def test_failure_does_not_break_main_action(self):
        t = self.tour(self.A)
        self.login(self.hiker)
        with mock.patch('badges.services.evaluate', side_effect=RuntimeError('kvar')), \
                self.assertLogs('badges.services', 'ERROR'):
            r = self.post('api_tours:register', t.pk)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(TourRegistration.objects.filter(tour=t, user=self.hiker).exists())
        self.assertEqual(codes(self.hiker), set())

    def test_backfill(self):
        self.attended(self.hiker, 1)
        call_command('badges_backfill', stdout=mock.MagicMock())
        self.assertTrue({'prvi-korak', 'prvi-vrh'} <= codes(self.hiker))
        call_command('badges_backfill', stdout=mock.MagicMock())
        self.assertEqual(UserBadge.objects.filter(user=self.hiker).count(), 2)


class MyBadgesApiTests(BadgeBase):
    def test_requires_login(self):
        self.assertEqual(self.c.get(reverse('api_me:badges')).status_code, 403)

    def test_only_own_badges_with_progress(self):
        services.evaluate(self.hiker)
        self.attended(self.guideA2, 3)
        self.login(self.guideA2)
        d = {b['code']: b for b in self.c.get(reverse('api_me:badges')).json()['results']}
        self.assertFalse(d['prvi-korak']['earned'])              # bedž planinara nije prenesen
        self.assertEqual((d['planinar-5']['progress'], d['planinar-5']['goal']), (3, 5))
        self.assertIn('prvi-put-na-celu', d)                     # vodič vidi i bedževe vodiča
        self.assertNotIn('osnivac', d)
        self.assertNotIn('cuvar-planine', d)

    def test_seen(self):
        services.evaluate(self.hiker)
        self.login(self.hiker)
        d = {b['code']: b for b in self.c.get(reverse('api_me:badges')).json()['results']}
        self.assertTrue(d['prvi-korak']['earned'] and not d['prvi-korak']['seen'])
        r = self.c.post(reverse('api_me:badges_seen'), '{}', content_type='application/json')   # bez CSRF
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.post('api_me:badges_seen').json(), {'updated': 1})
        self.assertFalse(UserBadge.objects.filter(user=self.hiker, seen=False).exists())
        services.evaluate(self.adminA)
        self.assertTrue(UserBadge.objects.filter(user=self.adminA, seen=False).exists())   # tuđi ostaju

    def test_system_admin_sees_only_system_badges(self):
        self.login(self.sys)
        roles = {b['role'] for b in self.c.get(reverse('api_me:badges')).json()['results']}
        self.assertEqual(roles, {'SISTEM'})
