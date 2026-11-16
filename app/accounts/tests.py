from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog

from .forms import GENERIC_LOGIN_ERROR
from .models import User

PW = 'Snijeg-Na-Bjelasnici-42'


class RegistrationTests(TestCase):
    def post(self, **over):
        data = {'email': 'ana@primjer.ba', 'first_name': 'Ana', 'last_name': 'Anić', 'phone': '',
                'password1': PW, 'password2': PW}
        data.update(over)
        return self.client.post(reverse('accounts:register'), data)

    def test_register_creates_hiker(self):
        r = self.post()
        self.assertRedirects(r, reverse('accounts:login'))
        u = User.objects.get(email='ana@primjer.ba')
        self.assertFalse(u.is_system_admin)
        self.assertTrue(u.check_password(PW))
        self.assertNotEqual(u.password, PW)

    def test_duplicate_email_gives_same_response(self):
        """Politika 4.4: javnost ne smije saznati da li nalog postoji."""
        first = self.post()
        second = self.post(first_name='Neko', last_name='Drugi')
        self.assertEqual(first.status_code, second.status_code)
        self.assertEqual(first['Location'], second['Location'])
        self.assertEqual(User.objects.filter(email='ana@primjer.ba').count(), 1)
        self.assertEqual(User.objects.get(email='ana@primjer.ba').first_name, 'Ana')

    def test_email_is_case_insensitive(self):
        self.post()
        self.post(email='ANA@Primjer.BA')
        self.assertEqual(User.objects.count(), 1)

    def test_weak_passwords_rejected(self):
        for pw in ['kratka1', 'password123', '1234567890123', 'ana@primjer.ba']:
            r = self.post(password1=pw, password2=pw)
            self.assertEqual(r.status_code, 200, pw)
        self.assertEqual(User.objects.count(), 0)

    def test_cannot_register_as_system_admin(self):
        """Mass assignment: dodatna polja u POST-u se ignorišu."""
        self.post(is_system_admin='on', is_active='on', failed_login_count='0')
        self.assertFalse(User.objects.get().is_system_admin)


class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('vodic@primjer.ba', PW, first_name='Vedo', last_name='Vodić')
        self.url = reverse('accounts:login')

    def login(self, pw, email='vodic@primjer.ba'):
        return self.client.post(self.url, {'username': email, 'password': pw})

    def test_login_ok(self):
        r = self.login(PW)
        self.assertRedirects(r, reverse('home'))
        self.assertTrue(AuditLog.objects.filter(action='LOGIN_USPJEH', user=self.user).exists())

    def test_generic_error_for_wrong_password_and_unknown_user(self):
        a = self.login('pogresna-lozinka-123')
        b = self.login(PW, email='nepostoji@primjer.ba')
        self.assertContains(a, GENERIC_LOGIN_ERROR)
        self.assertContains(b, GENERIC_LOGIN_ERROR)

    @override_settings(LOCKOUT_MAX_ATTEMPTS=5, LOCKOUT_MINUTES=15)
    def test_lockout_after_five_failures(self):
        for _ in range(5):
            self.login('pogresna-lozinka-123')
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked())
        # ni ispravna lozinka ne prolazi dok je nalog zaključan
        r = self.login(PW)
        self.assertContains(r, GENERIC_LOGIN_ERROR)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_lock_expires(self):
        User.objects.filter(pk=self.user.pk).update(locked_until=timezone.now() - timedelta(seconds=1))
        self.assertRedirects(self.login(PW), reverse('home'))

    def test_success_resets_counter(self):
        for _ in range(3):
            self.login('pogresna-lozinka-123')
        self.login(PW)
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 0)

    def test_blocked_user_cannot_login_and_session_dies(self):
        self.login(PW)
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        # postojeća sesija više ne važi
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 302)
        self.assertContains(self.login(PW), GENERIC_LOGIN_ERROR)

    def test_open_redirect_blocked(self):
        r = self.client.post(self.url + '?next=https://zlo.example/', {'username': 'vodic@primjer.ba', 'password': PW})
        self.assertRedirects(r, reverse('home'))

    def test_logout_requires_post(self):
        self.login(PW)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        self.client.post(reverse('accounts:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('p@primjer.ba', PW, first_name='Pero', last_name='Perić')

    def test_anonymous_redirected(self):
        r = self.client.get(reverse('accounts:profile'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('accounts:login'), r['Location'])

    def test_profile_cannot_change_protected_fields(self):
        self.client.force_login(self.user)
        self.client.post(reverse('accounts:profile'), {
            'first_name': 'Pero', 'last_name': 'Perić', 'phone': '061', 'emergency_contact_name': '',
            'emergency_contact_phone': '', 'health_notes': 'alergija na ubode',
            'email': 'hacker@primjer.ba', 'is_system_admin': 'on'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.health_notes, 'alergija na ubode')
        self.assertEqual(self.user.email, 'p@primjer.ba')
        self.assertFalse(self.user.is_system_admin)

    def test_password_change_requires_old_password(self):
        self.client.force_login(self.user)
        new = 'Novo-Ljeto-Na-Prenju-77'
        self.client.post(reverse('accounts:password_change'),
                         {'old_password': 'pogresna', 'new_password1': new, 'new_password2': new})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PW))
        self.client.post(reverse('accounts:password_change'),
                         {'old_password': PW, 'new_password1': new, 'new_password2': new})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))


class CsrfTests(TestCase):
    def test_login_requires_csrf(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse('accounts:login'), {'username': 'x@y.ba', 'password': 'x'})
        self.assertEqual(r.status_code, 403)
