"""F09 - zahtjev za registraciju društva preko API-ja."""
import json

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from accounts.permissions import admin_clubs
from audit.models import AuditLog

from .models import Club, ClubAdmin

PW = 'Snijeg-Na-Bjelasnici-42'


class ClubRequestApiTests(TestCase):
    def setUp(self):
        self.h = User.objects.create_user('h@p.ba', PW, first_name='H', last_name='H')
        self.sys = User.objects.create_system_admin('s@f.ba', PW, first_name='S', last_name='S')
        Club.objects.create(name='PD Ok', city='Sarajevo', status=Club.Status.APPROVED, created_by=self.h)
        self.c = Client(enforce_csrf_checks=True)

    def login(self, user):
        self.c.force_login(user)
        self.c.get(reverse('api_auth:csrf'))

    def post(self, data, csrf=True):
        headers = {'X-CSRFToken': self.c.cookies['csrftoken'].value} if csrf else {}
        return self.c.post(reverse('api_clubs:request'), json.dumps(data), content_type='application/json', headers=headers)

    def test_request_is_pending_and_gives_no_rights(self):
        self.login(self.h)
        self.assertTrue(self.c.get(reverse('api_clubs:request')).json()['canRequest'])
        r = self.post({'name': 'PD Novo', 'city': 'Zenica', 'status': 'ODOBRENO', 'createdBy': self.sys.pk})
        self.assertEqual(r.status_code, 201)
        club = Club.objects.get(name='PD Novo')
        self.assertEqual((club.status, club.created_by), (Club.Status.PENDING, self.h))
        self.assertTrue(ClubAdmin.objects.filter(club=club, user=self.h).exists())
        self.assertFalse(admin_clubs(self.h).filter(pk=club.pk).exists())     # prava tek nakon odobrenja
        self.assertTrue(AuditLog.objects.filter(action='DRUSTVO_ZAHTJEV').exists())
        self.assertFalse(self.c.get(reverse('api_clubs:request')).json()['canRequest'])
        self.assertEqual(self.c.get(reverse('api_clubs:detail', args=[club.pk])).status_code, 404)  # nije javno

    def test_only_one_pending_request(self):
        self.login(self.h)
        self.assertEqual(self.post({'name': 'PD A', 'city': 'X'}).status_code, 201)
        r = self.post({'name': 'PD B', 'city': 'X'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Club.objects.filter(created_by=self.h, status=Club.Status.PENDING).count(), 1)

    def test_duplicate_name_and_validation(self):
        self.login(self.h)
        r = self.post({'name': 'PD Ok', 'city': 'X'})
        self.assertEqual(r.json()['errors'], {'name': ['Ovaj naziv nije dostupan.']})
        r = self.post({'name': '', 'city': '', 'email': 'nije-email'})
        self.assertEqual(set(r.json()['errors']), {'name', 'city', 'email'})
        self.assertEqual(Club.objects.count(), 1)

    def test_roles_and_csrf(self):
        self.assertEqual(self.c.get(reverse('api_clubs:request')).status_code, 403)
        self.login(self.sys)
        self.assertEqual(self.post({'name': 'PD S', 'city': 'X'}).status_code, 403)
        self.login(self.h)
        self.assertEqual(self.post({'name': 'PD C', 'city': 'X'}, csrf=False).status_code, 403)
