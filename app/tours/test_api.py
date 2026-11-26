"""Javni API tura i društava: pravila vidljivosti (politika 4.4)."""
import json
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clubs.models import Club, ClubGuide, ClubMembership

from .models import Tour, TourGuide, TourRegistration

PW = 'Snijeg-Na-Bjelasnici-42'
ROUTE = [[43.7 + i * 0.001, 18.2 + i * 0.001] for i in range(120)]


class PublicApiBase(TestCase):
    def setUp(self):
        self.c = Client(enforce_csrf_checks=True)
        self.owner = User.objects.create_user('admin@drustvo.ba', PW, first_name='Adi', last_name='Admin')
        self.hiker = User.objects.create_user('tajni.ucesnik@primjer.ba', PW, first_name='Tajni', last_name='Učesnik',
                                              phone='061111222', health_notes='dijabetes')
        self.guide = User.objects.create_user('vodic@drustvo.ba', PW, first_name='Vedo', last_name='Vodić',
                                              phone='062333444')
        self.club = Club.objects.create(name='PD Bjelašnica', city='Sarajevo', status=Club.Status.APPROVED,
                                        created_by=self.owner, email='info@pd.ba')
        self.pending = Club.objects.create(name='PD Na čekanju', city='Mostar', created_by=self.owner)
        now = timezone.now()

        def tour(name, club=None, status=Tour.Status.PUBLISHED, days=5, **kw):
            return Tour.objects.create(
                club=club or self.club, name=name, start_at=now + timedelta(days=days),
                registration_deadline=now + timedelta(days=days - 1) if days > 1 else now - timedelta(days=30),
                meeting_point='Ilidža', difficulty=kw.pop('difficulty', Tour.Difficulty.MEDIUM), length_km=12.5,
                elevation_gain_m=800, duration_h=6, max_participants=2, status=status, created_by=self.owner, **kw)

        self.tour = tour
        self.visible = tour('Vidljiva tura', route=ROUTE, region='Bjelašnica')
        self.easy = tour('Laka tura', difficulty=Tour.Difficulty.EASY, days=10)
        self.hidden = [
            tour('Nacrt tura', status=Tour.Status.DRAFT),
            tour('Otkazana tura', status=Tour.Status.CANCELLED),
            tour('Daleka tura', days=45),
            tour('Prošla tura', days=-2),
            tour('Tura neodobrenog društva', club=self.pending),
        ]
        TourRegistration.objects.create(tour=self.visible, user=self.hiker)
        ClubGuide.objects.create(club=self.club, user=self.guide)
        TourGuide.objects.create(tour=self.visible, user=self.guide, status=TourGuide.Status.APPROVED)

    def get(self, name, *args, **params):
        return self.c.get(reverse(name, args=args), params)


class TourListApiTests(PublicApiBase):
    def test_only_public_tours(self):
        r = self.get('api_tours:list')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([t['name'] for t in r.json()['results']], ['Vidljiva tura', 'Laka tura'])

    def test_summary_fields_whitelisted(self):
        t = self.get('api_tours:list').json()['results'][0]
        self.assertEqual(set(t), {'id', 'name', 'club', 'region', 'startAt', 'difficulty', 'lengthKm', 'elevationGainM',
                                  'durationH', 'price', 'membersOnly', 'maxParticipants', 'freeSpots', 'start', 'trace'})
        self.assertEqual(t['freeSpots'], 1)
        self.assertEqual(t['lengthKm'], 12.5)
        self.assertEqual(t['start'], ROUTE[0])
        self.assertLessEqual(len(t['trace']), 41)
        self.assertEqual(t['trace'][-1], [round(c, 5) for c in ROUTE[-1]])

    def test_filters(self):
        names = lambda **p: [t['name'] for t in self.get('api_tours:list', **p).json()['results']]  # noqa: E731
        self.assertEqual(names(difficulty='LAKA'), ['Laka tura'])
        self.assertEqual(names(q='bjelašnica'), ['Vidljiva tura'])
        self.assertEqual(names(club=self.club.pk), ['Vidljiva tura', 'Laka tura'])
        later = (timezone.localdate() + timedelta(days=8)).isoformat()
        self.assertEqual(names(date_from=later), ['Laka tura'])

    def test_invalid_filter_is_400(self):
        for params in [{'difficulty': 'NEPOSTOJI'}, {'club': self.pending.pk}, {'date_from': 'jučer'}, {'q': 'x' * 81}]:
            r = self.get('api_tours:list', **params)
            self.assertEqual(r.status_code, 400, params)
            self.assertIn('errors', r.json())

    def test_unknown_params_ignored(self):
        self.assertEqual(self.get('api_tours:list', status='NACRT').status_code, 200)
        self.assertEqual(len(self.get('api_tours:list', status='NACRT').json()['results']), 2)

    def test_read_only(self):
        r = self.c.post(reverse('api_tours:list'), '{}', content_type='application/json')
        self.assertEqual(r.status_code, 403)          # CSRF prije svega
        self.c.get(reverse('api_auth:csrf'))
        token = self.c.cookies['csrftoken'].value
        r = self.c.post(reverse('api_tours:list'), '{}', content_type='application/json', headers={'X-CSRFToken': token})
        self.assertEqual(r.status_code, 405)

    def test_html_in_names_returned_as_plain_json_text(self):
        evil = '<img src=x onerror=alert(1)>'
        Tour.objects.filter(pk=self.visible.pk).update(name=evil)
        r = self.get('api_tours:list')
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertEqual(r.json()['results'][0]['name'], evil)


class TourDetailApiTests(PublicApiBase):
    def test_detail(self):
        r = self.get('api_tours:detail', self.visible.pk)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d['guides'], ['Vedo Vodić'])
        self.assertEqual(len(d['route']), len(ROUTE))
        self.assertIsNone(d['myRegistration'])
        self.assertFalse(d['deadlinePassed'])
        self.assertTrue(d['canRegister'])

    def test_hidden_tours_are_404(self):
        for t in self.hidden:
            r = self.get('api_tours:detail', t.pk)
            self.assertEqual(r.status_code, 404, t.name)
            self.assertNotIn(t.name, r.content.decode())
        self.assertEqual(self.get('api_tours:detail', 999999).status_code, 404)

    def test_no_private_data(self):
        body = self.get('api_tours:detail', self.visible.pk).content.decode()
        for leaked in ['tajni.ucesnik', 'Tajni', '061111222', '062333444', 'dijabetes', 'vodic@drustvo.ba',
                       'admin@drustvo.ba', 'created', 'password']:
            self.assertNotIn(leaked, body)

    def test_my_registration(self):
        self.c.force_login(self.hiker)
        d = self.get('api_tours:detail', self.visible.pk).json()
        self.assertEqual(d['myRegistration']['status'], TourRegistration.Status.REGISTERED)
        self.assertEqual(self.get('api_tours:detail', self.easy.pk).json()['myRegistration'], None)

    def test_system_admin_cannot_register(self):
        admin = User.objects.create_system_admin('sys@frostbite.ba', PW, first_name='S', last_name='A')
        self.c.force_login(admin)
        self.assertFalse(self.get('api_tours:detail', self.visible.pk).json()['canRegister'])


class StatsAndFiltersApiTests(PublicApiBase):
    def test_stats_count_only_public(self):
        d = self.get('api_tours:stats').json()
        self.assertEqual(d, {'tours': 2, 'clubs': 1, 'km': 25, 'elevation': 1600})

    def test_filters_only_approved_clubs(self):
        d = self.get('api_tours:filters').json()
        self.assertEqual([c['name'] for c in d['clubs']], ['PD Bjelašnica'])
        self.assertIn({'code': 'LAKA', 'label': 'Laka'}, d['difficulties'])


class ClubApiTests(PublicApiBase):
    def test_list_only_approved(self):
        d = self.get('api_clubs:list').json()['results']
        self.assertEqual([(c['name'], c['toursCount']) for c in d], [('PD Bjelašnica', 2)])
        self.assertNotIn('email', d[0])

    def test_detail(self):
        d = self.get('api_clubs:detail', self.club.pk).json()
        self.assertEqual(d['email'], 'info@pd.ba')
        self.assertEqual([t['name'] for t in d['tours']], ['Vidljiva tura', 'Laka tura'])
        self.assertIsNone(d['membership'])
        self.assertNotIn('admin@drustvo.ba', json.dumps(d))

    def test_pending_club_is_404(self):
        self.assertEqual(self.get('api_clubs:detail', self.pending.pk).status_code, 404)

    def test_my_membership(self):
        ClubMembership.objects.create(club=self.club, user=self.hiker, status=ClubMembership.Status.APPROVED)
        self.c.force_login(self.hiker)
        self.assertEqual(self.get('api_clubs:detail', self.club.pk).json()['membership']['status'], 'ODOBRENO')
