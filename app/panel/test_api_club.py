"""API panela admina društva: izolacija društava (ograničenje 2), IDOR, bez ličnih podataka (F27)."""
import json
from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from clubs.models import Club, ClubGuide, ClubMembership
from tours.models import Tour, TourGuide, TourRegistration

from .tests import Base


class ClubApiBase(Base):
    def setUp(self):
        super().setUp()
        self.c = Client(enforce_csrf_checks=True)

    def login(self, user):
        self.c.force_login(user)
        self.c.get(reverse('api_auth:csrf'))
        self.token = self.c.cookies['csrftoken'].value

    def url(self, name, *args):
        return reverse(f'api_manage:{name}', args=args)

    def get(self, name, *args):
        return self.c.get(self.url(name, *args))

    def send(self, method, name, *args, data=None, csrf=True):
        return getattr(self.c, method)(self.url(name, *args), json.dumps(data or {}), content_type='application/json',
                                       headers={'X-CSRFToken': self.token} if csrf else {})

    def tour_data(self, **over):
        start = timezone.localtime() + timedelta(days=10)
        d = {'name': 'Nova', 'region': 'R', 'description': '', 'startAt': start.strftime('%Y-%m-%dT%H:%M'),
             'registrationDeadline': (start - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'), 'meetingPoint': 'M',
             'difficulty': 'LAKA', 'lengthKm': 5, 'elevationGainM': 100, 'durationH': 2, 'maxParticipants': 10,
             'price': 0, 'membersOnly': False, 'requiredEquipment': '', 'route': [[43.7, 18.2], [43.71, 18.21]]}
        d.update(over)
        return d


class IsolationTests(ClubApiBase):
    def test_only_own_clubs(self):
        self.login(self.adminA)
        self.assertEqual([c['name'] for c in self.get('clubs').json()['results']], ['PD A'])
        self.assertEqual(self.get('dashboard', self.A.pk).status_code, 200)
        for name, args in [('dashboard', [self.B.pk]), ('tours', [self.B.pk]), ('members', [self.B.pk]),
                           ('guides', [self.B.pk]), ('profile', [self.B.pk]), ('tour', [self.B.pk, self.tB.pk])]:
            self.assertEqual(self.get(name, *args).status_code, 404, name)

    def test_idor_other_club_tour_via_own_club(self):
        self.login(self.adminA)
        self.assertEqual(self.get('tour', self.A.pk, self.tB.pk).status_code, 404)
        r = self.send('post', 'transition', self.A.pk, self.tB.pk, data={'action': 'cancel'})
        self.assertEqual(r.status_code, 404)
        self.tB.refresh_from_db()
        self.assertEqual(self.tB.status, Tour.Status.PUBLISHED)

    def test_non_admins_and_suspended(self):
        for u in [self.hiker, self.guideA, self.sys]:
            self.login(u)
            self.assertEqual(self.get('dashboard', self.A.pk).status_code, 404, u.email)
        Club.objects.filter(pk=self.A.pk).update(status=Club.Status.SUSPENDED)
        self.login(self.adminA)
        self.assertEqual(self.get('dashboard', self.A.pk).status_code, 404)

    def test_csrf_required(self):
        self.login(self.adminA)
        self.assertEqual(self.send('post', 'tours', self.A.pk, data=self.tour_data(), csrf=False).status_code, 403)

    def test_registrations_without_personal_data(self):
        self.login(self.adminA)
        body = self.get('tour', self.A.pk, self.tA.pk).content.decode()
        self.assertIn('Planinar', body)
        for leaked in ['TAJNA-DIJAGNOZA', '061 999 888', 'h@p.ba', '062 777 666', 'Mama']:
            self.assertNotIn(leaked, body)
        self.assertNotIn('h@p.ba', self.get('members', self.A.pk).content.decode())


class TourApiTests(ClubApiBase):
    def test_create_is_draft_in_own_club(self):
        self.login(self.adminA)
        r = self.send('post', 'tours', self.A.pk, data=self.tour_data(status='OBJAVLJENA', club=self.B.pk, createdBy=self.sys.pk))
        self.assertEqual(r.status_code, 201)
        t = Tour.objects.get(name='Nova')
        self.assertEqual((t.club, t.status, t.created_by), (self.A, Tour.Status.DRAFT, self.adminA))
        self.assertEqual(t.route, [[43.7, 18.2], [43.71, 18.21]])
        self.assertTrue(AuditLog.objects.filter(action='TURA_KREIRANA').exists())

    def test_validation(self):
        self.login(self.adminA)
        start = timezone.localtime() + timedelta(days=10)
        for over in [{'route': [[200, 18], [43, 18]]}, {'route': [['<b>', 1], [43, 18]]}, {'route': {'a': 1}},
                     {'route': [[43, 18]] * 501}, {'route': [[43, 18]]}, {'name': ''}, {'difficulty': 'X'},
                     {'registrationDeadline': (start + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')},
                     {'startAt': '2000-01-01T10:00'}, {'maxParticipants': 0}, {'price': -5}, {'lengthKm': 'abc'}]:
            r = self.send('post', 'tours', self.A.pk, data=self.tour_data(**over))
            self.assertEqual(r.status_code, 400, over)
            self.assertIn('errors', r.json())
        self.assertFalse(Tour.objects.filter(name='Nova').exists())
        r = self.send('post', 'tours', self.A.pk, data=self.tour_data(registrationDeadline=(start + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')))
        self.assertIn('registrationDeadline', r.json()['errors'])

    def test_edit_and_locks(self):
        self.login(self.adminA)
        d = self.get('tour', self.A.pk, self.tA.pk).json()
        self.assertTrue(d['editable'])
        form = {**d['form'], 'name': 'Promijenjeno', 'maxParticipants': 12}
        self.assertEqual(self.send('put', 'tour', self.A.pk, self.tA.pk, data=form).status_code, 200)
        self.tA.refresh_from_db()
        self.assertEqual((self.tA.name, self.tA.max_participants), ('Promijenjeno', 12))
        TourRegistration.objects.create(tour=self.tA, user=self.guideA2)
        r = self.send('put', 'tour', self.A.pk, self.tA.pk, data={**form, 'maxParticipants': 1})
        self.assertIn('maxParticipants', r.json()['errors'])
        for st in [Tour.Status.DONE, Tour.Status.CANCELLED]:
            Tour.objects.filter(pk=self.tA.pk).update(status=st)
            self.assertEqual(self.send('put', 'tour', self.A.pk, self.tA.pk, data={**form, 'name': 'X'}).status_code, 400)
        self.tA.refresh_from_db()
        self.assertEqual(self.tA.name, 'Promijenjeno')

    def test_transitions(self):
        self.login(self.adminA)
        draft = self.tour(self.A, status=Tour.Status.DRAFT)
        act = lambda a: self.send('post', 'transition', self.A.pk, draft.pk, data={'action': a})  # noqa: E731
        self.assertEqual(self.get('tour', self.A.pk, draft.pk).json()['transitions'], ['publish'])
        self.assertEqual(act('cancel').status_code, 400)
        self.assertEqual(act('publish').status_code, 200)
        self.assertEqual(act('cancel').status_code, 200)
        self.assertEqual(act('publish').status_code, 400)
        self.assertEqual(act('obrisi').status_code, 404)
        self.assertEqual(self.send('post', 'transition', self.A.pk, draft.pk, data={'action': 1}).status_code, 404)


class GuidesAndMembersApiTests(ClubApiBase):
    def test_add_guide_same_message(self):
        self.login(self.adminA)
        a = self.send('post', 'guides', self.A.pk, data={'email': 'h@p.ba'}).json()
        b = self.send('post', 'guides', self.A.pk, data={'email': 'nema@nikoga.ba'}).json()
        c = self.send('post', 'guides', self.A.pk, data={'email': 's@f.ba'}).json()
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertTrue(ClubGuide.objects.filter(club=self.A, user=self.hiker, is_active=True).exists())
        self.assertFalse(ClubGuide.objects.filter(user=self.sys).exists())
        self.assertEqual(self.send('post', 'guides', self.A.pk, data={'email': 'nije-email'}).status_code, 400)

    def test_remove_guide_only_own_club(self):
        gB = ClubGuide.objects.create(club=self.B, user=self.hiker)
        self.login(self.adminA)
        self.assertEqual(self.send('post', 'guide_remove', self.A.pk, gB.pk).status_code, 404)
        gA = ClubGuide.objects.get(club=self.A, user=self.guideA2)
        self.assertEqual(self.send('post', 'guide_remove', self.A.pk, gA.pk).status_code, 200)
        gA.refresh_from_db()
        self.assertFalse(gA.is_active)

    def test_guide_application_and_assign(self):
        app = TourGuide.objects.create(tour=self.tA, user=self.guideA2)
        self.login(self.adminA)
        self.assertEqual(self.send('post', 'decide', self.A.pk, self.tA.pk, app.pk, data={'decision': 'x'}).status_code, 404)
        self.assertEqual(self.send('post', 'decide', self.A.pk, self.tA.pk, app.pk, data={'decision': 'approve'}).status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, TourGuide.Status.APPROVED)
        new = self.tour(self.A, name='Bez vodiča')
        g = ClubGuide.objects.get(club=self.A, user=self.guideA)
        self.assertEqual([x['id'] for x in self.get('tour', self.A.pk, new.pk).json()['assignable']], sorted(
            ClubGuide.objects.filter(club=self.A, is_active=True).values_list('pk', flat=True)))
        self.assertEqual(self.send('post', 'assign', self.A.pk, new.pk, data={'guideId': g.pk}).status_code, 200)
        self.assertTrue(TourGuide.objects.filter(tour=new, user=self.guideA, status='ODOBREN').exists())
        gB = ClubGuide.objects.create(club=self.B, user=self.hiker)
        self.assertEqual(self.send('post', 'assign', self.A.pk, new.pk, data={'guideId': gB.pk}).status_code, 404)
        self.assertEqual(self.send('post', 'assign', self.A.pk, new.pk, data={'guideId': '1'}).status_code, 404)

    def test_membership_decisions(self):
        m = ClubMembership.objects.create(club=self.A, user=self.hiker)
        self.login(self.adminB)
        self.assertEqual(self.send('post', 'member_decide', self.B.pk, m.pk, data={'decision': 'approve'}).status_code, 404)
        self.login(self.adminA)
        self.assertEqual(len(self.get('members', self.A.pk).json()['pending']), 1)
        self.assertEqual(self.send('post', 'member_decide', self.A.pk, m.pk, data={'decision': 'approve'}).status_code, 200)
        m.refresh_from_db()
        self.assertEqual((m.status, m.valid_until.month, m.decided_by), ('ODOBRENO', 12, self.adminA))
        self.assertEqual(self.send('post', 'member_decide', self.A.pk, m.pk, data={'decision': 'reject'}).status_code, 404)

    def test_profile(self):
        self.login(self.adminA)
        r = self.send('put', 'profile', self.A.pk, data={'city': 'Sarajevo', 'description': 'Opis', 'email': 'info@a.ba',
                                                         'phone': '033', 'name': 'Hakovano', 'status': 'ODOBRENO'})
        self.assertEqual(r.status_code, 200)
        self.A.refresh_from_db()
        self.assertEqual((self.A.name, self.A.city), ('PD A', 'Sarajevo'))
        self.assertEqual(self.send('put', 'profile', self.A.pk, data={'city': '', 'email': 'x'}).status_code, 400)

    def test_dashboard_numbers(self):
        self.login(self.adminA)
        d = self.get('dashboard', self.A.pk).json()
        self.assertEqual(d['phases']['active'], 1)
        self.assertEqual(d['fill'], {'taken': 1, 'capacity': 10, 'pct': 10})
        self.assertEqual(len(d['months']), 6)
        self.assertNotIn('TAJNA', json.dumps(d))
