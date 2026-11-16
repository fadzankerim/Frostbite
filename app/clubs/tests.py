from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.permissions import admin_clubs

from .models import Club, ClubAdmin, ClubMembership

PW = 'Snijeg-Na-Bjelasnici-42'


class ClubTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('o@d.ba', PW, first_name='O', last_name='O')
        self.h = User.objects.create_user('h@p.ba', PW, first_name='H', last_name='H')
        self.sys = User.objects.create_system_admin('s@f.ba', PW, first_name='S', last_name='S')
        self.club = Club.objects.create(name='PD Ok', city='Sarajevo', status=Club.Status.APPROVED, created_by=self.owner)
        self.pending = Club.objects.create(name='PD Čeka', city='Tuzla', created_by=self.owner)

    def test_public_list_hides_unapproved(self):
        r = self.client.get(reverse('clubs:list'))
        self.assertContains(r, 'PD Ok')
        self.assertNotContains(r, 'PD Čeka')
        self.assertEqual(self.client.get(reverse('clubs:detail', args=[self.pending.pk])).status_code, 404)

    def test_membership_request_once(self):
        self.client.force_login(self.h)
        self.client.post(reverse('clubs:membership_request', args=[self.club.pk]))
        self.client.post(reverse('clubs:membership_request', args=[self.club.pk]))
        self.assertEqual(ClubMembership.objects.filter(user=self.h).count(), 1)
        self.assertEqual(ClubMembership.objects.get(user=self.h).status, 'ZAHTJEV')

    def test_membership_request_to_pending_club_404(self):
        self.client.force_login(self.h)
        r = self.client.post(reverse('clubs:membership_request', args=[self.pending.pk]))
        self.assertEqual(r.status_code, 404)

    def test_sysadmin_cannot_request_membership(self):
        self.client.force_login(self.sys)
        r = self.client.post(reverse('clubs:membership_request', args=[self.club.pk]))
        self.assertEqual(r.status_code, 403)

    def test_club_registration_is_pending_and_gives_no_rights(self):
        self.client.force_login(self.h)
        self.client.post(reverse('clubs:register'), {
            'name': 'PD Novo', 'city': 'Zenica', 'description': '', 'email': '', 'phone': '',
            'status': 'ODOBRENO'})                          # pokušaj podmetanja statusa
        club = Club.objects.get(name='PD Novo')
        self.assertEqual(club.status, Club.Status.PENDING)
        self.assertTrue(ClubAdmin.objects.filter(club=club, user=self.h).exists())
        self.assertFalse(admin_clubs(self.h).exists())      # prava tek nakon odobrenja

    def test_only_one_pending_club_request(self):
        self.client.force_login(self.h)
        for name in ['PD A', 'PD B']:
            self.client.post(reverse('clubs:register'), {'name': name, 'city': 'X'})
        self.assertEqual(Club.objects.filter(created_by=self.h).count(), 1)

    def test_duplicate_club_name(self):
        self.client.force_login(self.h)
        r = self.client.post(reverse('clubs:register'), {'name': 'PD Ok', 'city': 'X'})
        self.assertContains(r, 'Ovaj naziv nije dostupan')
