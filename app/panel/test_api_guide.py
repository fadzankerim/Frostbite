"""API panela vodiča: ista pravila kao HTML panel (ograničenja 1 i 2, politika 4.5)."""
import json
from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from clubs.models import ClubGuide
from tours.models import Tour, TourGuide, TourRegistration

from .tests import Base


class GuideApiTests(Base):
    def setUp(self):
        super().setUp()
        self.c = Client(enforce_csrf_checks=True)

    def login(self, user):
        self.c.force_login(user)
        self.c.get(reverse('api_auth:csrf'))
        self.token = self.c.cookies['csrftoken'].value

    def get(self, name, *args):
        return self.c.get(reverse(name, args=args))

    def post(self, name, *args, data=None, csrf=True):
        return self.c.post(reverse(name, args=args), json.dumps(data or {}), content_type='application/json',
                           headers={'X-CSRFToken': self.token} if csrf else {})

    def make_tour_today(self):
        Tour.objects.filter(pk=self.tA.pk).update(start_at=timezone.now() - timedelta(hours=2),
                                                  registration_deadline=timezone.now() - timedelta(days=1),
                                                  status=Tour.Status.CLOSED)

    def test_dashboard(self):
        tA2 = self.tour(self.A, name='Bez vodiča')
        self.tour(self.B, name='Tuđe društvo')
        self.login(self.guideA)
        d = self.get('api_guide:dashboard').json()
        self.assertEqual([t['name'] for t in d['myTours']], ['Tura PD A'])
        self.assertEqual([(t['name'], t['applied']) for t in d['openTours']], [(tA2.name, False)])

    def test_only_guides(self):
        for u in [self.hiker, self.adminA, self.sys]:
            self.login(u)
            self.assertEqual(self.get('api_guide:dashboard').status_code, 403, u.email)
        self.c.logout()
        self.assertEqual(self.get('api_guide:dashboard').status_code, 403)

    def test_participants_with_personal_data_and_audit(self):
        self.login(self.guideA)
        r = self.get('api_guide:tour', self.tA.pk)
        self.assertEqual(r.status_code, 200)
        p = r.json()['participants'][0]
        self.assertEqual((p['healthNotes'], p['emergencyContactPhone']), ('TAJNA-DIJAGNOZA', '062 777 666'))
        self.assertNotIn('email', p)
        self.assertIn('no-store', r['Cache-Control'])
        self.assertTrue(AuditLog.objects.filter(action='PRISTUP_LICNIM_PODACIMA', user=self.guideA).exists())

    def test_other_guides_and_window(self):
        self.login(self.guideA2)                                    # isto društvo, nije vodič ove ture
        self.assertEqual(self.get('api_guide:tour', self.tA.pk).status_code, 404)
        TourGuide.objects.create(tour=self.tB, user=self.guideA2)   # tuđe društvo, samo prijava
        self.assertEqual(self.get('api_guide:tour', self.tB.pk).status_code, 404)
        self.login(self.guideA)
        Tour.objects.filter(pk=self.tA.pk).update(start_at=timezone.now() - timedelta(days=8),
                                                  registration_deadline=timezone.now() - timedelta(days=9))
        self.assertEqual(self.get('api_guide:tour', self.tA.pk).status_code, 404)

    def test_removed_guide_loses_access(self):
        ClubGuide.objects.filter(user=self.guideA).update(is_active=False)
        self.login(self.guideA)
        self.assertEqual(self.get('api_guide:tour', self.tA.pk).status_code, 403)

    def test_apply(self):
        tA2 = self.tour(self.A, name='Druga')
        self.login(self.guideA2)
        self.assertEqual(self.post('api_guide:apply', self.tB.pk).status_code, 404)
        self.assertEqual(self.post('api_guide:apply', tA2.pk, csrf=False).status_code, 403)
        self.assertEqual(self.post('api_guide:apply', tA2.pk).status_code, 201)
        r = self.post('api_guide:apply', tA2.pk)
        self.assertEqual(r.json()['detail'], 'Već ste se prijavili za vođenje ove ture.')
        self.assertTrue(self.get('api_guide:dashboard').json()['openTours'][0]['applied'])

    def test_close(self):
        self.login(self.guideA)
        self.assertEqual(self.post('api_guide:close', self.tA.pk).status_code, 200)
        self.tA.refresh_from_db()
        self.assertEqual(self.tA.status, Tour.Status.CLOSED)
        self.assertEqual(self.post('api_guide:close', self.tA.pk).status_code, 400)

    def test_attendance_and_report(self):
        self.make_tour_today()
        other = TourRegistration.objects.create(tour=self.tB, user=self.guideA2)
        self.login(self.guideA)
        d = self.get('api_guide:tour', self.tA.pk).json()
        self.assertTrue(d['attendanceOpen'] and d['canReport'])
        for bad in [None, 'x', [self.reg.pk, 'x'], [True]]:
            self.assertEqual(self.post('api_guide:attendance', self.tA.pk, data={'present': bad}).status_code, 400)
        r = self.post('api_guide:attendance', self.tA.pk, data={'present': [self.reg.pk, other.pk]})
        self.assertEqual(r.json()['present'], 1)
        self.reg.refresh_from_db(); other.refresh_from_db()
        self.assertEqual((self.reg.attendance, other.attendance), ('PRISUSTVOVAO', ''))
        self.assertEqual(self.post('api_guide:report', self.tA.pk, data={'text': ''}).status_code, 400)
        self.assertEqual(self.post('api_guide:report', self.tA.pk, data={'text': 'Sve u redu.'}).status_code, 201)
        self.tA.refresh_from_db()
        self.assertEqual((self.tA.status, self.tA.report.attendees_count), (Tour.Status.DONE, 1))
        self.assertEqual(self.post('api_guide:report', self.tA.pk, data={'text': 'Opet'}).status_code, 400)

    def test_attendance_not_before_tour_day(self):
        self.login(self.guideA)
        self.assertFalse(self.get('api_guide:tour', self.tA.pk).json()['attendanceOpen'])
        r = self.post('api_guide:attendance', self.tA.pk, data={'present': [self.reg.pk]})
        self.assertEqual(r.status_code, 400)
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.attendance, '')
