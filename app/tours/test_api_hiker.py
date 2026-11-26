"""API planinara: prijave na ture, lista čekanja, odjava, odabir, članstva, profil, lozinka.
Svi zahtjevi idu sa CSRF provjerom, kao iz pregledača."""
import json
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import AuditLog
from clubs.models import Club, ClubGuide, ClubMembership

from .models import Tour, TourGuide, TourRegistration

PW = 'Snijeg-Na-Bjelasnici-42'


class Api(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('admin@drustvo.ba', PW, first_name='Adi', last_name='Admin')
        self.ana = User.objects.create_user('ana@primjer.ba', PW, first_name='Ana', last_name='Anić',
                                            health_notes='alergija')
        self.bob = User.objects.create_user('bob@primjer.ba', PW, first_name='Bob', last_name='Bobić')
        self.sys = User.objects.create_system_admin('sys@frostbite.ba', PW, first_name='S', last_name='A')
        self.club = Club.objects.create(name='PD Bjelašnica', city='Sarajevo', status=Club.Status.APPROVED, created_by=self.owner)
        self.pending = Club.objects.create(name='PD Čeka', city='Tuzla', created_by=self.owner)
        now = timezone.now()

        def tour(name, days=5, deadline_days=None, **kw):
            dl = now + timedelta(days=deadline_days if deadline_days is not None else days - 1)
            return Tour.objects.create(
                club=kw.pop('club', self.club), name=name, start_at=now + timedelta(days=days), registration_deadline=dl,
                meeting_point='Ilidža', difficulty=Tour.Difficulty.MEDIUM, length_km=10, elevation_gain_m=500,
                duration_h=5, max_participants=kw.pop('maxp', 1), status=kw.pop('status', Tour.Status.PUBLISHED),
                created_by=self.owner, **kw)

        self.tour = tour
        self.t1 = tour('Tura 1')
        self.t2 = tour('Tura 2', days=8, maxp=5)
        self.members = tour('Za članove', members_only=True, maxp=5)
        self.c = self.client_for(None)

    def client_for(self, user):
        c = Client(enforce_csrf_checks=True)
        if user:
            c.force_login(user)
        c.get(reverse('api_auth:csrf'))
        c.token = c.cookies['csrftoken'].value
        return c

    def call(self, c, method, name, *args, data=None, csrf=True):
        headers = {'X-CSRFToken': c.token} if csrf else {}
        body = json.dumps(data) if data is not None else ''
        return getattr(c, method)(reverse(name, args=args), body, content_type='application/json', headers=headers)


class RegisterApiTests(Api):
    def test_register_and_waitlist(self):
        a, b = self.client_for(self.ana), self.client_for(self.bob)
        r = self.call(a, 'post', 'api_tours:register', self.t1.pk)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['status'], 'PRIJAVLJEN')
        r = self.call(b, 'post', 'api_tours:register', self.t1.pk)           # max 1 -> lista čekanja
        self.assertEqual(r.json()['status'], 'NA_LISTI_CEKANJA')
        r = self.call(a, 'post', 'api_tours:register', self.t1.pk)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['detail'], 'Već ste prijavljeni na ovu turu.')
        self.assertEqual(self.call(a, 'get', 'api_tours:detail', self.t1.pk).json()['myRegistration']['status'], 'PRIJAVLJEN')

    def test_requires_login_csrf_and_hiker_role(self):
        self.assertEqual(self.call(self.c, 'post', 'api_tours:register', self.t1.pk).status_code, 403)
        a = self.client_for(self.ana)
        self.assertEqual(self.call(a, 'post', 'api_tours:register', self.t1.pk, csrf=False).status_code, 403)
        s = self.client_for(self.sys)
        self.assertEqual(self.call(s, 'post', 'api_tours:register', self.t1.pk).status_code, 403)
        self.assertFalse(TourRegistration.objects.exists())

    def test_rules_from_services(self):
        a = self.client_for(self.ana)
        closed = self.tour('Rok prošao', days=3, deadline_days=-1)
        draft = self.tour('Nacrt', status=Tour.Status.DRAFT)
        foreign = self.tour('Neodobreno', club=self.pending)
        for t, msg in [(closed, 'Rok za prijavu je istekao.'), (draft, 'Prijave na ovu turu nisu otvorene.'),
                       (foreign, 'Prijave na ovu turu nisu otvorene.'), (self.members, 'Tura je samo za članove')]:
            r = self.call(a, 'post', 'api_tours:register', t.pk)
            self.assertEqual(r.status_code, 400, t.name)
            self.assertIn(msg, r.json()['detail'])
        ClubMembership.objects.create(club=self.club, user=self.ana, status=ClubMembership.Status.APPROVED)
        self.assertEqual(self.call(a, 'post', 'api_tours:register', self.members.pk).status_code, 201)

    def test_guide_cannot_join_own_tour(self):
        ClubGuide.objects.create(club=self.club, user=self.bob)
        TourGuide.objects.create(tour=self.t2, user=self.bob, status=TourGuide.Status.APPROVED)
        r = self.call(self.client_for(self.bob), 'post', 'api_tours:register', self.t2.pk)
        self.assertEqual(r.status_code, 400)

    def test_ignores_extra_fields(self):
        a = self.client_for(self.ana)
        self.call(a, 'post', 'api_tours:register', self.t2.pk, data={'status': 'PRIJAVLJEN', 'user': self.bob.pk})
        reg = TourRegistration.objects.get()
        self.assertEqual(reg.user, self.ana)


class MyRegistrationsApiTests(Api):
    def test_list_and_cancel_promotes_waitlist(self):
        a, b = self.client_for(self.ana), self.client_for(self.bob)
        self.call(a, 'post', 'api_tours:register', self.t1.pk)
        self.call(b, 'post', 'api_tours:register', self.t1.pk)
        d = self.call(a, 'get', 'api_me:registrations').json()
        self.assertEqual(len(d['upcoming']), 1)
        item = d['upcoming'][0]
        self.assertTrue(item['canCancel'])
        self.assertTrue(item['tour']['public'])
        r = self.call(a, 'post', 'api_me:cancel', item['id'])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(TourRegistration.objects.get(user=self.bob).status, 'PRIJAVLJEN')
        d = self.call(a, 'get', 'api_me:registrations').json()
        self.assertEqual((len(d['upcoming']), d['history'][0]['status']), (0, 'ODJAVLJEN'))

    def test_cannot_cancel_someone_elses_registration(self):
        """IDOR: tuđa prijava se ponaša kao nepostojeća."""
        self.call(self.client_for(self.bob), 'post', 'api_tours:register', self.t2.pk)
        bobs = TourRegistration.objects.get(user=self.bob)
        r = self.call(self.client_for(self.ana), 'post', 'api_me:cancel', bobs.pk)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['detail'], 'Prijava nije pronađena.')
        bobs.refresh_from_db()
        self.assertEqual(bobs.status, 'PRIJAVLJEN')

    def test_only_own_registrations_listed(self):
        self.call(self.client_for(self.bob), 'post', 'api_tours:register', self.t2.pk)
        d = self.call(self.client_for(self.ana), 'get', 'api_me:registrations').json()
        self.assertEqual(d, {'upcoming': [], 'history': []})

    def test_cancel_after_deadline_rejected(self):
        t = self.tour('Uskoro', days=3, deadline_days=1, maxp=5)
        a = self.client_for(self.ana)
        self.call(a, 'post', 'api_tours:register', t.pk)
        Tour.objects.filter(pk=t.pk).update(registration_deadline=timezone.now() - timedelta(hours=1))
        reg = TourRegistration.objects.get()
        self.assertFalse(self.call(a, 'get', 'api_me:registrations').json()['upcoming'][0]['canCancel'])
        self.assertEqual(self.call(a, 'post', 'api_me:cancel', reg.pk).status_code, 400)


class SelectionApiTests(Api):
    def test_anonymous_can_select_but_must_login_to_confirm(self):
        r = self.call(self.c, 'post', 'api_selection:list', data={'tourId': self.t1.pk})
        self.assertEqual(r.json()['ids'], [self.t1.pk])
        self.assertEqual(self.call(self.c, 'post', 'api_selection:confirm').status_code, 403)

    def test_add_remove_confirm(self):
        a = self.client_for(self.ana)
        for t in (self.t1, self.t2, self.members):
            self.call(a, 'post', 'api_selection:list', data={'tourId': t.pk})
        self.assertTrue(self.call(a, 'get', 'api_tours:detail', self.t2.pk).json()['inSelection'])
        r = self.call(a, 'delete', 'api_selection:item', self.t2.pk)
        self.assertEqual(r.json()['ids'], [self.t1.pk, self.members.pk])
        res = self.call(a, 'post', 'api_selection:confirm').json()['results']
        self.assertEqual([(x['name'], x['ok']) for x in res], [('Tura 1', True), ('Za članove', False)])
        self.assertEqual(self.call(a, 'get', 'api_selection:list').json()['ids'], [])

    def test_only_public_tours_and_limit(self):
        a = self.client_for(self.ana)
        draft = self.tour('Nacrt', status=Tour.Status.DRAFT)
        self.assertEqual(self.call(a, 'post', 'api_selection:list', data={'tourId': draft.pk}).status_code, 404)
        for bad in ['1', None, True, [1], {'x': 1}]:
            self.assertEqual(self.call(a, 'post', 'api_selection:list', data={'tourId': bad}).status_code, 400, bad)
        extra = [self.tour(f'T{i}', maxp=5) for i in range(10)]
        for t in extra:
            self.call(a, 'post', 'api_selection:list', data={'tourId': t.pk})
        r = self.call(a, 'post', 'api_selection:list', data={'tourId': self.t1.pk})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.call(a, 'get', 'api_selection:list').json()['ids']), 10)


class MembershipApiTests(Api):
    def test_request_once_and_list(self):
        a = self.client_for(self.ana)
        self.assertTrue(self.call(a, 'get', 'api_clubs:detail', self.club.pk).json()['canRequest'])
        r = self.call(a, 'post', 'api_clubs:membership', self.club.pk)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.call(a, 'post', 'api_clubs:membership', self.club.pk).status_code, 400)
        d = self.call(a, 'get', 'api_clubs:detail', self.club.pk).json()
        self.assertEqual((d['membership']['status'], d['canRequest']), ('ZAHTJEV', False))
        mine = self.call(a, 'get', 'api_me:memberships').json()['results']
        self.assertEqual([m['club']['name'] for m in mine], ['PD Bjelašnica'])
        self.assertTrue(AuditLog.objects.filter(action='CLANSTVO_ZAHTJEV').exists())

    def test_rejected_can_request_again(self):
        ClubMembership.objects.create(club=self.club, user=self.ana, status=ClubMembership.Status.REJECTED)
        a = self.client_for(self.ana)
        self.assertTrue(self.call(a, 'get', 'api_clubs:detail', self.club.pk).json()['canRequest'])
        self.assertEqual(self.call(a, 'post', 'api_clubs:membership', self.club.pk).status_code, 201)

    def test_pending_club_and_roles(self):
        a = self.client_for(self.ana)
        self.assertEqual(self.call(a, 'post', 'api_clubs:membership', self.pending.pk).status_code, 404)
        self.assertEqual(self.call(self.client_for(self.sys), 'post', 'api_clubs:membership', self.club.pk).status_code, 403)
        self.assertEqual(self.call(self.c, 'get', 'api_me:memberships').status_code, 403)


class ProfileApiTests(Api):
    def test_get_own_profile_only(self):
        self.assertEqual(self.call(self.c, 'get', 'api_me:profile').status_code, 403)
        d = self.call(self.client_for(self.ana), 'get', 'api_me:profile').json()
        self.assertEqual((d['email'], d['healthNotes']), ('ana@primjer.ba', 'alergija'))
        self.assertNotIn('password', d)

    def test_update_cannot_touch_protected_fields(self):
        a = self.client_for(self.ana)
        r = self.call(a, 'put', 'api_me:profile', data={
            'firstName': 'Ana', 'lastName': 'Anić', 'phone': '061', 'emergencyContactName': 'Mama',
            'emergencyContactPhone': '062', 'healthNotes': 'nema', 'email': 'hacker@zlo.example',
            'isSystemAdmin': True, 'is_system_admin': True, 'is_active': False})
        self.assertEqual(r.status_code, 200)
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.email, self.ana.is_system_admin, self.ana.is_active, self.ana.health_notes),
                         ('ana@primjer.ba', False, True, 'nema'))
        self.assertTrue(AuditLog.objects.filter(action='PROFIL_IZMJENA', user=self.ana).exists())

    def test_validation(self):
        r = self.call(self.client_for(self.ana), 'put', 'api_me:profile', data={'firstName': '', 'lastName': 'x' * 61})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.json()['errors']), {'firstName', 'lastName'})

    def test_password_change(self):
        a = self.client_for(self.ana)
        other = self.client_for(self.ana)                      # druga sesija istog korisnika
        new = 'Novo-Ljeto-Na-Prenju-77'
        r = self.call(a, 'post', 'api_me:password', data={'oldPassword': 'pogresna', 'newPassword': new, 'newPasswordConfirm': new})
        self.assertEqual(r.status_code, 400)
        self.assertIn('oldPassword', r.json()['errors'])
        r = self.call(a, 'post', 'api_me:password', data={'oldPassword': PW, 'newPassword': 'kratka', 'newPasswordConfirm': 'kratka'})
        self.assertIn('newPasswordConfirm', r.json()['errors'])
        r = self.call(a, 'post', 'api_me:password', data={'oldPassword': PW, 'newPassword': new, 'newPasswordConfirm': new})
        self.assertEqual(r.status_code, 200)
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password(new))
        self.assertTrue(self.call(a, 'get', 'api_auth:me').json()['authenticated'])        # ova sesija ostaje
        self.assertFalse(self.call(other, 'get', 'api_auth:me').json()['authenticated'])   # ostale ne
