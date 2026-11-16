from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clubs.models import Club

from .models import Tour, TourRegistration

PW = 'Snijeg-Na-Bjelasnici-42'


class PublicTourListTests(TestCase):
    """F01 i politika 4.4: šta javnost smije, a šta ne smije vidjeti."""

    def setUp(self):
        self.owner = User.objects.create_user('admin@drustvo.ba', PW, first_name='Adi', last_name='Admin')
        self.hiker = User.objects.create_user('tajni.ucesnik@primjer.ba', PW, first_name='Tajni', last_name='Učesnik')
        self.ok_club = Club.objects.create(name='PD Bjelašnica', city='Sarajevo', status=Club.Status.APPROVED, created_by=self.owner)
        self.pending = Club.objects.create(name='PD Na čekanju', city='Mostar', created_by=self.owner)
        now = timezone.now()

        def tour(name, club=None, status=Tour.Status.PUBLISHED, days=5):
            return Tour.objects.create(
                club=club or self.ok_club, name=name, start_at=now + timedelta(days=days),
                registration_deadline=now + timedelta(days=days - 1) if days > 1 else now - timedelta(days=30),
                meeting_point='Ilidža', difficulty=Tour.Difficulty.MEDIUM, length_km=12, elevation_gain_m=800,
                duration_h=6, max_participants=10, status=status, created_by=self.owner)

        self.visible = tour('Vidljiva tura')
        tour('Nacrt tura', status=Tour.Status.DRAFT)
        tour('Otkazana tura', status=Tour.Status.CANCELLED)
        tour('Daleka tura', days=45)
        tour('Prošla tura', days=-2)
        tour('Tura neodobrenog društva', club=self.pending)
        TourRegistration.objects.create(tour=self.visible, user=self.hiker)

    def test_only_allowed_tours_visible(self):
        for url in [reverse('home'), reverse('tours:list')]:
            r = self.client.get(url)
            self.assertContains(r, 'Vidljiva tura')
            for hidden in ['Nacrt tura', 'Otkazana tura', 'Daleka tura', 'Prošla tura', 'Tura neodobrenog društva']:
                self.assertNotContains(r, hidden)

    def test_map_points_only_public_data(self):
        Tour.objects.update(route=[[43.7, 18.2], [43.8, 18.3]])
        r = self.client.get(reverse('tours:list'))
        points = r.context['map_points']
        self.assertEqual([p['name'] for p in points], ['Vidljiva tura'])
        self.assertEqual(set(points[0]), {'id', 'url', 'name', 'club', 'lat', 'lng', 'date', 'difficulty',
                                          'difficulty_label', 'free', 'max'})

    def test_map_data_escapes_html_in_names(self):
        Tour.objects.filter(pk=self.visible.pk).update(
            name='<img src=x onerror=alert(1)></script><script>alert(2)</script>', route=[[43.7, 18.2], [43.8, 18.3]])
        html = self.client.get(reverse('tours:list')).content.decode()
        self.assertNotIn('<script>alert(2)</script>', html)
        self.assertNotIn('<img src=x onerror', html)
        self.assertIn('\\u003Cscript\\u003Ealert(2)', html)        # json_script escapes < > &

    def test_free_spots_without_participant_data(self):
        r = self.client.get(reverse('home'))
        self.assertContains(r, '9 slobodnih od 10')
        self.assertNotContains(r, 'Tajni')
        self.assertNotContains(r, 'tajni.ucesnik')


from django.core.exceptions import ValidationError  # noqa: E402

from clubs.models import ClubMembership  # noqa: E402

from .models import TourGuide, validate_route  # noqa: E402


class RegistrationRulesTests(TestCase):
    """F10, F11 - ograničenja 3 i 4 iz politike."""

    def setUp(self):
        self.admin = User.objects.create_user('a@d.ba', PW, first_name='A', last_name='A')
        self.club = Club.objects.create(name='PD Test', city='Sarajevo', status=Club.Status.APPROVED, created_by=self.admin)
        self.h1 = User.objects.create_user('h1@p.ba', PW, first_name='H', last_name='Jedan')
        self.h2 = User.objects.create_user('h2@p.ba', PW, first_name='H', last_name='Dva')
        self.h3 = User.objects.create_user('h3@p.ba', PW, first_name='H', last_name='Tri')
        self.guide = User.objects.create_user('g@p.ba', PW, first_name='G', last_name='Vodič')
        self.sys = User.objects.create_system_admin('s@f.ba', PW, first_name='S', last_name='Admin')
        self.tour = self.make_tour(max_participants=2)

    def make_tour(self, **kw):
        now = timezone.now()
        data = dict(club=self.club, name='Tura', start_at=now + timedelta(days=5),
                    registration_deadline=now + timedelta(days=4), meeting_point='X',
                    difficulty=Tour.Difficulty.EASY, length_km=5, elevation_gain_m=100, duration_h=2,
                    max_participants=10, status=Tour.Status.PUBLISHED, created_by=self.admin)
        data.update(kw)
        return Tour.objects.create(**data)

    def reg(self, user, tour=None):
        self.client.force_login(user)
        return self.client.post(reverse('tours:register', args=[(tour or self.tour).pk]))

    def status_of(self, user, tour=None):
        r = TourRegistration.objects.filter(user=user, tour=tour or self.tour).exclude(status='ODJAVLJEN').first()
        return r.status if r else None

    def test_capacity_and_waitlist(self):
        self.reg(self.h1); self.reg(self.h2); self.reg(self.h3)
        self.assertEqual(self.status_of(self.h1), 'PRIJAVLJEN')
        self.assertEqual(self.status_of(self.h2), 'PRIJAVLJEN')
        self.assertEqual(self.status_of(self.h3), 'NA_LISTI_CEKANJA')

    def test_cancel_promotes_waitlist(self):
        self.reg(self.h1); self.reg(self.h2); self.reg(self.h3)
        reg = TourRegistration.objects.get(user=self.h1, tour=self.tour)
        self.client.force_login(self.h1)
        self.client.post(reverse('tours:cancel', args=[reg.pk]))
        self.assertIsNone(self.status_of(self.h1))
        self.assertEqual(self.status_of(self.h3), 'PRIJAVLJEN')

    def test_no_double_registration(self):
        self.reg(self.h1); self.reg(self.h1)
        self.assertEqual(TourRegistration.objects.filter(user=self.h1).count(), 1)

    def test_deadline_passed(self):
        now = timezone.now()
        t = self.make_tour(registration_deadline=now - timedelta(hours=1))
        self.reg(self.h1, t)
        self.assertIsNone(self.status_of(self.h1, t))

    def test_draft_and_cancelled_tours_closed(self):
        for st in [Tour.Status.DRAFT, Tour.Status.CANCELLED, Tour.Status.CLOSED, Tour.Status.DONE]:
            t = self.make_tour(status=st)
            self.reg(self.h1, t)
            self.assertIsNone(self.status_of(self.h1, t), st)

    def test_members_only(self):
        t = self.make_tour(members_only=True)
        self.reg(self.h1, t)
        self.assertIsNone(self.status_of(self.h1, t))
        ClubMembership.objects.create(club=self.club, user=self.h1, status='ODOBRENO',
                                      valid_until=timezone.localdate() - timedelta(days=1))
        self.reg(self.h1, t)
        self.assertIsNone(self.status_of(self.h1, t), 'isteklo članstvo ne važi')
        ClubMembership.objects.filter(user=self.h1).update(valid_until=timezone.localdate() + timedelta(days=30))
        self.reg(self.h1, t)
        self.assertEqual(self.status_of(self.h1, t), 'PRIJAVLJEN')

    def test_guide_cannot_join_own_tour(self):
        TourGuide.objects.create(tour=self.tour, user=self.guide, status=TourGuide.Status.APPROVED)
        self.reg(self.guide)
        self.assertIsNone(self.status_of(self.guide))

    def test_system_admin_forbidden(self):
        r = self.reg(self.sys)
        self.assertEqual(r.status_code, 403)
        self.assertIsNone(self.status_of(self.sys))

    def test_anonymous_redirected_to_login(self):
        r = self.client.post(reverse('tours:register', args=[self.tour.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('accounts:login'), r['Location'])

    def test_cannot_cancel_someone_elses_registration(self):
        self.reg(self.h1)
        reg = TourRegistration.objects.get(user=self.h1)
        self.client.force_login(self.h2)
        self.client.post(reverse('tours:cancel', args=[reg.pk]))
        self.assertEqual(self.status_of(self.h1), 'PRIJAVLJEN')

    def test_cancel_requires_post(self):
        self.reg(self.h1)
        reg = TourRegistration.objects.get(user=self.h1)
        self.assertEqual(self.client.get(reverse('tours:cancel', args=[reg.pk])).status_code, 405)

    def test_my_registrations_shows_only_own(self):
        self.reg(self.h2)
        self.client.force_login(self.h1)
        r = self.client.get(reverse('tours:my_registrations'))
        self.assertNotContains(r, 'Tura</strong>')

    def test_selection_confirm_registers_all(self):
        t2 = self.make_tour(name='Druga')
        self.client.post(reverse('tours:selection_add', args=[self.tour.pk]))
        self.client.post(reverse('tours:selection_add', args=[t2.pk]))
        self.client.force_login(self.h1)       # odabir preživi prijavu? ne - nova sesija; dodaj ponovo
        self.client.post(reverse('tours:selection_add', args=[self.tour.pk]))
        self.client.post(reverse('tours:selection_add', args=[t2.pk]))
        self.client.post(reverse('tours:selection_confirm'))
        self.assertEqual(self.status_of(self.h1), 'PRIJAVLJEN')
        self.assertEqual(self.status_of(self.h1, t2), 'PRIJAVLJEN')

    def test_selection_rejects_non_public_tours(self):
        draft = self.make_tour(status=Tour.Status.DRAFT)
        r = self.client.post(reverse('tours:selection_add', args=[draft.pk]))
        self.assertEqual(r.status_code, 404)

    def test_detail_404_for_hidden_tours(self):
        draft = self.make_tour(status=Tour.Status.DRAFT)
        self.assertEqual(self.client.get(reverse('tours:detail', args=[draft.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('tours:detail', args=[self.tour.pk])).status_code, 200)

    def test_detail_does_not_leak_participants(self):
        self.reg(self.h1)
        self.client.logout()
        r = self.client.get(reverse('tours:detail', args=[self.tour.pk]))
        self.assertNotContains(r, 'h1@p.ba')
        self.assertNotContains(r, 'Jedan')


class RouteValidationTests(TestCase):
    def test_valid(self):
        validate_route([])
        validate_route([[43.7, 18.2], [43.71, 18.21]])

    def test_invalid(self):
        bad = [[[43.7, 18.2]], [[91, 18], [43, 18]], [['43.7', 18.2], [43, 18]], 'tekst',
               [[43, 18, 1], [43, 18]], [[True, 18], [43, 18]], [[43, 18]] * 501,
               [{'lat': 43}, [43, 18]], [['<script>', 1], [43, 18]]]
        for v in bad:
            with self.assertRaises(ValidationError, msg=str(v)[:40]):
                validate_route(v)


class HomePageTests(TestCase):
    def test_intro_and_stats_shown_without_filters(self):
        r = self.client.get(reverse('home'))
        self.assertContains(r, 'Kako funkcioniše')
        self.assertContains(r, 'data-count=')

    def test_tours_page_filters(self):
        r = self.client.get(reverse('tours:list') + '?q=xyz')
        self.assertContains(r, 'Rezultati pretrage')
        self.assertContains(r, 'Nijedna tura ne odgovara filterima')

    def test_no_inline_scripts_or_styles(self):
        """CSP (script-src 'self'): stranica ne smije imati inline JavaScript ni style atribute."""
        import re
        for url in [reverse('home'), reverse('tours:list')]:
            html = self.client.get(url).content.decode()
            for tag in re.findall(r'<script[^>]*>', html):
                self.assertTrue('src=' in tag or 'application/json' in tag, tag)
            self.assertNotIn(' style="', html)
            self.assertNotIn(' onclick=', html)

    def test_favicon_redirect(self):
        r = self.client.get('/favicon.ico')
        self.assertEqual(r.status_code, 301)
        self.assertTrue(r['Location'].endswith('favicon.ico'))


class GpsAndGpxTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('o@d.ba', PW, first_name='O', last_name='O')
        self.club = Club.objects.create(name='PD <b>Test</b>', city='X', status=Club.Status.APPROVED, created_by=owner)
        now = timezone.now()
        base = dict(club=self.club, start_at=now + timedelta(days=5), registration_deadline=now + timedelta(days=4),
                    meeting_point='Parking & "kod" <crkve>', difficulty=Tour.Difficulty.EASY, length_km=5,
                    elevation_gain_m=100, duration_h=2, max_participants=10, created_by=owner)
        self.tour = Tour.objects.create(name='Tura <script>alert(1)</script>', status=Tour.Status.PUBLISHED,
                                        route=[[43.7238, 18.2841], [43.7068, 18.2566]], **base)
        self.no_route = Tour.objects.create(name='Bez rute', status=Tour.Status.PUBLISHED, **base)
        self.draft = Tour.objects.create(name='Nacrt', status=Tour.Status.DRAFT, route=[[43.7, 18.2], [43.8, 18.3]], **base)

    def test_gpx_download(self):
        r = self.client.get(reverse('tours:gpx', args=[self.tour.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/gpx+xml; charset=utf-8')
        self.assertIn('attachment;', r['Content-Disposition'])
        body = r.content.decode()
        self.assertIn('<trkpt lat="43.723800" lon="18.284100"/>', body)
        self.assertNotIn('<script>', body)
        self.assertIn('&lt;script&gt;', body)
        self.assertNotIn('<b>', body)
        import xml.dom.minidom
        xml.dom.minidom.parseString(r.content)              # ispravan XML uprkos specijalnim znakovima

    def test_gpx_only_public_tours_with_route(self):
        self.assertEqual(self.client.get(reverse('tours:gpx', args=[self.draft.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('tours:gpx', args=[self.no_route.pk])).status_code, 404)

    def test_detail_shows_start_coordinates_and_links(self):
        r = self.client.get(reverse('tours:detail', args=[self.tour.pk]))
        self.assertContains(r, '43.723800, 18.284100')
        self.assertContains(r, 'https://www.google.com/maps/dir/?api=1&amp;destination=43.723800,18.284100')
        self.assertContains(r, 'rel="noopener noreferrer"')
        r = self.client.get(reverse('tours:detail', args=[self.no_route.pk]))
        self.assertNotContains(r, 'GPS koordinate polaska')
