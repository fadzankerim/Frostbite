"""Testovi auth API-ja (/api/auth/). Svi zahtjevi idu sa uključenom CSRF provjerom,
kao iz pravog pregledača."""
import json
from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from clubs.models import Club

from .forms import GENERIC_LOGIN_ERROR
from .models import User
from .services import REGISTER_DONE_MSG

PW = 'Snijeg-Na-Bjelasnici-42'


class ApiClientMixin:
    def setUp(self):
        self.c = Client(enforce_csrf_checks=True)
        self.token = None

    def csrf(self):
        r = self.c.get(reverse('api_auth:csrf'))
        self.assertEqual(r.status_code, 200)
        self.token = r.json()['csrfToken']
        return r

    def post(self, name, data=None, token=True):
        if token and self.token is None:
            self.csrf()
        headers = {'X-CSRFToken': self.token} if token else {}
        return self.c.post(reverse(name), json.dumps(data or {}), content_type='application/json',
                           headers=headers)

    def login(self, pw=PW, email='vodic@primjer.ba'):
        r = self.post('api_auth:login', {'email': email, 'password': pw})
        if r.status_code == 200:
            self.token = r.json()['csrfToken']      # Django mijenja token pri prijavi
        return r

    def me(self):
        return self.c.get(reverse('api_auth:me')).json()


class CsrfApiTests(ApiClientMixin, TestCase):
    def test_csrf_endpoint_sets_cookie_and_returns_token(self):
        r = self.csrf()
        self.assertIn('csrftoken', r.cookies)
        self.assertTrue(r.cookies['csrftoken']['httponly'])
        self.assertTrue(self.token)
        self.assertIn('no-store', r['Cache-Control'])

    def test_login_without_csrf_rejected(self):
        """Login CSRF: anonimni POST bez tokena mora biti odbijen."""
        User.objects.create_user('vodic@primjer.ba', PW, first_name='V', last_name='V')
        r = self.post('api_auth:login', {'email': 'vodic@primjer.ba', 'password': PW}, token=False)
        self.assertEqual(r.status_code, 403)
        self.assertIn('CSRF', r.json()['detail'])
        self.assertFalse(self.me()['authenticated'])

    def test_register_and_logout_without_csrf_rejected(self):
        self.assertEqual(self.post('api_auth:register', {}, token=False).status_code, 403)
        self.assertEqual(self.post('api_auth:logout', token=False).status_code, 403)

    def test_only_json_no_browsable_api(self):
        r = self.c.get(reverse('api_auth:me'), headers={'Accept': 'text/html'})
        self.assertEqual(r['Content-Type'], 'application/json')

    def test_form_encoded_body_rejected(self):
        self.csrf()
        r = self.c.post(reverse('api_auth:login'), {'email': 'a@b.ba', 'password': 'x'},
                        headers={'X-CSRFToken': self.token})
        self.assertEqual(r.status_code, 415)


class LoginApiTests(ApiClientMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('vodic@primjer.ba', PW, first_name='Vedo', last_name='Vodić')

    def test_login_ok(self):
        old_token = self.csrf().json()['csrfToken']
        r = self.login()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body['authenticated'])
        self.assertEqual(body['user']['email'], 'vodic@primjer.ba')
        self.assertNotIn('password', json.dumps(body))
        # Django mijenja CSRF token pri prijavi; novi se vraća frontendu
        self.assertNotEqual(body['csrfToken'], old_token)
        self.assertTrue(r.cookies['sessionid']['httponly'])
        self.assertTrue(AuditLog.objects.filter(action='LOGIN_USPJEH', user=self.user).exists())
        self.assertTrue(self.me()['authenticated'])

    def test_email_case_insensitive(self):
        self.assertEqual(self.login(email='VODIC@Primjer.ba').status_code, 200)

    def test_generic_error_for_wrong_password_and_unknown_user(self):
        a = self.login('pogresna-lozinka-123')
        b = self.login(email='nepostoji@primjer.ba')
        self.assertEqual(a.status_code, 400)
        self.assertEqual(a.json(), b.json())
        self.assertEqual(a.json(), {'detail': GENERIC_LOGIN_ERROR})

    def test_missing_fields(self):
        r = self.post('api_auth:login', {})
        self.assertEqual(r.status_code, 400)
        self.assertIn('detail', r.json())

    @override_settings(LOCKOUT_MAX_ATTEMPTS=5, LOCKOUT_MINUTES=15)
    def test_lockout_after_five_failures(self):
        for _ in range(5):
            self.login('pogresna-lozinka-123')
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked())
        r = self.login()
        self.assertEqual(r.json(), {'detail': GENERIC_LOGIN_ERROR})
        self.assertFalse(self.me()['authenticated'])

    def test_success_resets_counter(self):
        for _ in range(3):
            self.login('pogresna-lozinka-123')
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 3)
        self.login()
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 0)

    def test_lock_expires(self):
        User.objects.filter(pk=self.user.pk).update(locked_until=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.login().status_code, 200)

    def test_blocked_user_cannot_login_and_session_dies(self):
        self.login()
        self.assertTrue(self.me()['authenticated'])
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertFalse(self.me()['authenticated'])
        self.assertEqual(self.login().json(), {'detail': GENERIC_LOGIN_ERROR})

    def test_new_session_on_login(self):
        """Fiksacija sesije: ID sesije se mijenja pri prijavi."""
        self.c.get(reverse('api_auth:csrf'))
        s = self.c.session
        s['x'] = 1
        s.save()
        before = self.c.cookies['sessionid'].value
        self.login()
        self.assertNotEqual(self.c.cookies['sessionid'].value, before)

    def test_logout(self):
        self.login()
        r = self.post('api_auth:logout')
        self.assertEqual(r.status_code, 204)
        self.assertFalse(self.me()['authenticated'])
        self.assertTrue(AuditLog.objects.filter(action='ODJAVA', user=self.user).exists())

    def test_old_csrf_token_rejected_after_login(self):
        old = self.csrf().json()['csrfToken']
        self.login()
        self.token = old
        self.assertEqual(self.post('api_auth:logout').status_code, 403)

    def test_logout_requires_post(self):
        self.login()
        self.assertEqual(self.c.get(reverse('api_auth:logout')).status_code, 405)
        self.assertTrue(self.me()['authenticated'])

    def test_password_change_kills_api_session(self):
        self.login()
        u = User.objects.get(pk=self.user.pk)
        u.set_password('Novo-Ljeto-Na-Prenju-77')
        u.save()
        self.assertFalse(self.me()['authenticated'])


class MeApiTests(ApiClientMixin, TestCase):
    def test_anonymous(self):
        self.assertEqual(self.me(), {'authenticated': False, 'user': None})

    def test_roles(self):
        admin = User.objects.create_user('admin@primjer.ba', PW, first_name='A', last_name='A')
        club = Club.objects.create(name='PD A', city='X', status=Club.Status.APPROVED, created_by=admin)
        club.admins.create(user=admin)
        self.c.force_login(admin)
        self.assertEqual(self.me()['user']['roles'], {'systemAdmin': False, 'clubAdmin': True, 'guide': False})
        # suspendovano društvo ne daje ulogu
        Club.objects.filter(pk=club.pk).update(status=Club.Status.SUSPENDED)
        self.assertFalse(self.me()['user']['roles']['clubAdmin'])

    def test_sensitive_fields_not_exposed(self):
        u = User.objects.create_user('p@primjer.ba', PW, first_name='P', last_name='P',
                                     health_notes='dijabetes')
        self.c.force_login(u)
        body = json.dumps(self.me())
        for leaked in ('dijabetes', 'password', 'failed_login', 'locked'):
            self.assertNotIn(leaked, body)


class RegisterApiTests(ApiClientMixin, TestCase):
    def register(self, **over):
        data = {'email': 'ana@primjer.ba', 'firstName': 'Ana', 'lastName': 'Anić', 'phone': '',
                'password': PW, 'passwordConfirm': PW}
        data.update(over)
        return self.post('api_auth:register', data)

    def test_register_creates_hiker(self):
        r = self.register()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json(), {'detail': REGISTER_DONE_MSG})
        u = User.objects.get(email='ana@primjer.ba')
        self.assertTrue(u.check_password(PW))
        self.assertFalse(u.is_system_admin)
        self.assertFalse(self.me()['authenticated'])     # registracija ne prijavljuje

    def test_duplicate_email_gives_same_response(self):
        first = self.register()
        second = self.register(firstName='Neko', email='ANA@primjer.ba')
        self.assertEqual((first.status_code, first.json()), (second.status_code, second.json()))
        self.assertEqual(User.objects.get().first_name, 'Ana')
        self.assertTrue(AuditLog.objects.filter(action='REGISTRACIJA_DUPLIKAT').exists())

    def test_validation_errors_use_api_field_names(self):
        r = self.register(password='kratka1', passwordConfirm='kratka1', firstName='')
        self.assertEqual(r.status_code, 400)
        errors = r.json()['errors']
        self.assertIn('password', errors)
        self.assertIn('firstName', errors)

    def test_password_mismatch(self):
        r = self.register(passwordConfirm=PW + 'x')
        self.assertIn('passwordConfirm', r.json()['errors'])
        self.assertEqual(User.objects.count(), 0)

    def test_cannot_register_as_system_admin(self):
        self.register(is_system_admin=True, isSystemAdmin=True, is_active=True)
        self.assertFalse(User.objects.get().is_system_admin)
