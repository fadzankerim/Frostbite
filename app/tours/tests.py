"""Validacija rute (model) i GPX izvoz. Pravila vidljivosti i prijava su u test_api*.py."""
import xml.dom.minidom
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clubs.models import Club

from .models import Tour, validate_route

PW = 'Snijeg-Na-Bjelasnici-42'


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


class GpxTests(TestCase):
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
        r = self.client.get(reverse('api_tours:gpx', args=[self.tour.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/gpx+xml; charset=utf-8')
        self.assertIn('attachment;', r['Content-Disposition'])
        body = r.content.decode()
        self.assertIn('<trkpt lat="43.723800" lon="18.284100"/>', body)
        self.assertNotIn('<script>', body)
        self.assertIn('&lt;script&gt;', body)
        self.assertNotIn('<b>', body)
        xml.dom.minidom.parseString(r.content)              # ispravan XML uprkos specijalnim znakovima

    def test_gpx_only_public_tours_with_route(self):
        self.assertEqual(self.client.get(reverse('api_tours:gpx', args=[self.draft.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('api_tours:gpx', args=[self.no_route.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('api_tours:gpx', args=[self.tour.pk])).status_code, 405)


class NoHtmlTests(TestCase):
    """Django služi samo API: nepoznate putanje daju JSON 404 bez internih detalja."""

    def test_unknown_paths_are_json_404(self):
        for path in ['/', '/ture/', '/nalog/prijava/', '/api/nepostoji/', '/static/css/style.css', '/admin/']:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 404, path)
            self.assertEqual(r['Content-Type'], 'application/json', path)
            self.assertEqual(r.json(), {'detail': 'Nije pronađeno.'})
