"""API sistemskog admina: samo sistemski admin, bez osjetljivih podataka, blokiranje gasi sesije."""
import json

from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse

from audit.models import AuditLog
from clubs.models import Club, ClubAdmin

from .test_base import Base


class SystemApiTests(Base):
    def setUp(self):
        super().setUp()
        self.c = Client(enforce_csrf_checks=True)

    def login(self, user):
        self.c.force_login(user)
        self.c.get(reverse('api_auth:csrf'))
        self.token = self.c.cookies['csrftoken'].value

    def get(self, name, *args, **params):
        return self.c.get(reverse(f'api_system:{name}', args=args), params)

    def post(self, name, *args, data=None, csrf=True):
        return self.c.post(reverse(f'api_system:{name}', args=args), json.dumps(data or {}),
                           content_type='application/json', headers={'X-CSRFToken': self.token} if csrf else {})

    def test_only_system_admin(self):
        for u in [self.hiker, self.adminA, self.guideA]:
            self.login(u)
            for name in ['dashboard', 'clubs', 'users', 'audit']:
                self.assertEqual(self.get(name).status_code, 403, (u.email, name))
            self.assertEqual(self.post('user_toggle', self.hiker.pk).status_code, 403)
        self.c.logout()
        self.assertEqual(self.get('audit').status_code, 403)

    def test_dashboard_no_personal_data(self):
        self.login(self.sys)
        r = self.get('dashboard')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['logins']), 14)
        for leaked in ['TAJNA-DIJAGNOZA', '061 999 888', '062 777 666', 'Mama']:
            self.assertNotIn(leaked, r.content.decode())

    def test_users_search_paging_and_fields(self):
        self.login(self.sys)
        d = self.get('users', q='h@p').json()
        self.assertEqual([u['email'] for u in d['results']], ['h@p.ba'])
        self.assertEqual(set(d['results'][0]), {'id', 'email', 'firstName', 'lastName', 'isActive', 'isSystemAdmin',
                                                'dateJoined', 'locked', 'isSelf'})
        self.assertNotIn('TAJNA', self.get('users').content.decode())
        self.assertEqual(self.get('users', page='abc').json()['page'], 1)
        self.assertEqual(self.get('users', page='999').json()['page'], 1)       # Paginator: zadnja strana
        self.assertEqual(self.get('users', q='x' * 500).status_code, 200)

    def test_block_kills_sessions_and_not_self(self):
        other = Client()
        other.force_login(self.hiker)
        self.login(self.sys)
        r = self.post('user_toggle', self.hiker.pk)
        self.assertEqual((r.status_code, r.json()['isActive']), (200, False))
        self.assertEqual(other.get(reverse('api_auth:me')).json()['authenticated'], False)
        self.assertFalse(any(s.get_decoded().get('_auth_user_id') == str(self.hiker.pk) for s in Session.objects.all()))
        self.assertEqual(self.post('user_toggle', self.hiker.pk).json()['isActive'], True)
        r = self.post('user_toggle', self.sys.pk)
        self.assertEqual(r.status_code, 400)
        self.sys.refresh_from_db()
        self.assertTrue(self.sys.is_active)
        self.assertEqual(self.post('user_toggle', 999999).status_code, 404)
        self.assertEqual(self.post('user_toggle', self.hiker.pk, csrf=False).status_code, 403)

    def test_club_decisions(self):
        pending = Club.objects.create(name='PD Novo', city='Z', created_by=self.hiker)
        ClubAdmin.objects.create(club=pending, user=self.hiker)
        self.login(self.sys)
        d = self.get('clubs').json()
        self.assertEqual(d['pending'][0]['actions'], ['approve', 'reject'])
        self.assertEqual(self.post('club_decide', pending.pk, data={'action': 'suspend'}).status_code, 400)
        self.assertEqual(self.post('club_decide', pending.pk, data={'action': 'obrisi'}).status_code, 404)
        self.assertEqual(self.post('club_decide', pending.pk, data={'action': 'approve'}).status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, Club.Status.APPROVED)
        self.assertTrue(AuditLog.objects.filter(action='DRUSTVO_ODOBRENO').exists())
        self.assertEqual(self.post('club_decide', self.A.pk, data={'action': 'suspend'}).status_code, 200)
        self.login(self.adminA)
        self.assertEqual(self.c.get(reverse('api_manage:dashboard', args=[self.A.pk])).status_code, 404)

    def test_audit_read_only_and_filter(self):
        AuditLog.objects.create(action='TEST_AKCIJA', details='<script>x</script>')
        self.login(self.sys)
        d = self.get('audit', action='TEST').json()
        self.assertEqual([e['action'] for e in d['results']], ['TEST_AKCIJA'])
        self.assertEqual(self.c.delete(reverse('api_system:audit'), headers={'X-CSRFToken': self.token}).status_code, 405)
        self.assertEqual(self.post('audit').status_code, 405)
