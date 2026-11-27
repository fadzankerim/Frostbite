"""Obavještenja (handoff 5.5): outbox u transakciji radnje, bez osjetljivih podataka, postavke,
pregled, odjava jednim klikom, ponovni pokušaji, ograničenja i zakazana obavještenja."""
import json
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from clubs.models import ClubMembership
from panel.test_base import PW, Base
from tours.models import Tour, TourGuide, TourRegistration

from . import sender, services
from .categories import BY_CODE
from .models import NotificationPreference, Outbox

SENSITIVE = ['TAJNA-DIJAGNOZA', '061 999 888', '062 777 666', 'Mama']


def send(now=None):
    return sender.send_due(now or timezone.now())


class NotificationBase(Base):
    def setUp(self):
        super().setUp()
        self.c = Client(enforce_csrf_checks=True)

    def login(self, user):
        self.c.force_login(user)
        self.c.get(reverse('api_auth:csrf'))
        self.token = self.c.cookies['csrftoken'].value

    def call(self, method, name, *args, data=None):
        return getattr(self.c, method)(reverse(name, args=args), json.dumps(data or {}), content_type='application/json',
                                       headers={'X-CSRFToken': self.token})

    def rows(self, user, template=None):
        qs = Outbox.objects.filter(user=user)
        return qs.filter(template=template) if template else qs

    def all_mail_text(self):
        return ' '.join(m.subject + m.body + ''.join(a[0] for a in m.alternatives) for m in mail.outbox)


class OutboxTransactionTests(NotificationBase):
    def test_registration_writes_outbox_and_sends(self):
        t = self.tour(self.A)
        self.login(self.guideA2)
        self.assertEqual(self.call('post', 'api_tours:register', t.pk).status_code, 201)
        row = self.rows(self.guideA2, 'prijava_potvrda').get()
        self.assertEqual(row.status, Outbox.Status.PENDING)
        self.assertEqual(send(), (1, 0, 0))
        m = mail.outbox[0]
        self.assertEqual(m.to, [self.guideA2.email])
        self.assertIn(t.name, m.subject)
        self.assertIn(f'/ture/{t.pk}', m.body)
        self.assertTrue(AuditLog.objects.filter(action='EMAIL_POSLAN', user=self.guideA2).exists())

    def test_failed_action_writes_nothing(self):
        members = self.tour(self.A, members_only=True)
        self.login(self.guideA2)
        self.assertEqual(self.call('post', 'api_tours:register', members.pk).status_code, 400)
        self.assertFalse(Outbox.objects.exists())

    def test_notification_error_does_not_break_action(self):
        t = self.tour(self.A)
        self.login(self.guideA2)
        with mock.patch('notifications.events.notify', side_effect=RuntimeError('kvar')), \
                self.assertLogs('notifications.events', 'ERROR'):
            self.assertEqual(self.call('post', 'api_tours:register', t.pk).status_code, 201)
        self.assertTrue(TourRegistration.objects.filter(tour=t, user=self.guideA2).exists())


class PrivacyTests(NotificationBase):
    def test_guide_emails_never_contain_personal_data(self):
        """Vodič dobija ime i brojke, nikad telefon, hitni kontakt ni zdravstvene napomene."""
        NotificationPreference.objects.create(user=self.guideA, category='ucesnici', mode='odmah')
        self.reg.delete()
        self.login(self.hiker)
        self.call('post', 'api_tours:register', self.tA.pk)
        send()
        guide_mail = [m for m in mail.outbox if m.to == [self.guideA.email]]
        self.assertEqual(len(guide_mail), 1)
        self.assertIn('Planinar Test', guide_mail[0].body)
        text = self.all_mail_text()
        for s in SENSITIVE:
            self.assertNotIn(s, text)

    def test_user_text_is_escaped_in_html(self):
        t = self.tour(self.A, name='<script>alert(1)</script> & tura')
        self.login(self.guideA2)
        self.call('post', 'api_tours:register', t.pk)
        send()
        html = mail.outbox[0].alternatives[0][0]
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('\n', mail.outbox[0].subject)


class PreferenceTests(NotificationBase):
    def test_off_means_no_row(self):
        services.set_mode(self.guideA2, 'moje_ture', 'iskljuceno')
        self.login(self.guideA2)
        self.call('post', 'api_tours:register', self.tour(self.A).pk)
        self.assertFalse(self.rows(self.guideA2).exists())

    def test_security_cannot_be_disabled(self):
        self.login(self.hiker)
        r = self.call('put', 'api_me:notifications', data={'sigurnost': 'iskljuceno'})
        self.assertEqual(r.status_code, 400)
        with self.assertRaises(ValueError):
            services.set_mode(self.hiker, 'sigurnost', 'iskljuceno')
        NotificationPreference.objects.create(user=self.hiker, category='sigurnost', mode='iskljuceno')  # podmetnuto
        self.assertEqual(services.mode_for(self.hiker, 'sigurnost'), 'odmah')

    def test_api_shows_only_own_role_categories(self):
        self.assertEqual(self.c.get(reverse('api_me:notifications')).status_code, 403)
        self.login(self.hiker)
        codes = {c['code'] for c in self.c.get(reverse('api_me:notifications')).json()['results']}
        self.assertIn('moje_ture', codes)
        self.assertNotIn('drustvo', codes)
        self.assertNotIn('zahtjevi_drustava', codes)
        self.assertEqual(self.call('put', 'api_me:notifications', data={'drustvo': 'iskljuceno'}).status_code, 400)
        r = self.call('put', 'api_me:notifications', data={'nove_ture': 'pregled'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(services.mode_for(self.hiker, 'nove_ture'), 'pregled')
        self.login(self.sys)
        codes = {c['code'] for c in self.c.get(reverse('api_me:notifications')).json()['results']}
        self.assertEqual(codes, {'sigurnost', 'zahtjevi_drustava'})


class DigestTests(NotificationBase):
    def test_guide_daily_digest_groups_changes(self):
        t = self.tour(self.A, days=5)
        TourGuide.objects.create(tour=t, user=self.guideA2, status=TourGuide.Status.APPROVED)
        for u in (self.hiker, self.adminB):
            self.login(u)
            self.call('post', 'api_tours:register', t.pk)
        rows = self.rows(self.guideA2, 'ucesnici_promjena')
        self.assertEqual(rows.count(), 2)
        self.assertTrue(all(r.digest for r in rows))
        send()                                                       # potvrde planinarima idu odmah
        self.assertFalse([m for m in mail.outbox if m.to == [self.guideA2.email]])   # pregled još nije dospio
        morning = rows.first().send_after
        self.assertEqual(timezone.localtime(morning).hour, services.DIGEST_HOUR)
        send(morning + timedelta(minutes=1))
        digest = [m for m in mail.outbox if m.to == [self.guideA2.email]]
        self.assertEqual(len(digest), 1)
        self.assertIn('Dnevni pregled', digest[0].subject)
        self.assertEqual(digest[0].body.count(t.name), 2)

    def test_late_cancellation_is_urgent(self):
        Tour.objects.filter(pk=self.tA.pk).update(start_at=timezone.now() + timedelta(hours=20),
                                                  registration_deadline=timezone.now() + timedelta(hours=10))
        self.login(self.hiker)
        self.call('post', 'api_me:cancel', self.reg.pk)
        row = self.rows(self.guideA, 'ucesnici_promjena').get()
        self.assertFalse(row.digest)

    def test_weekly_digest_lands_on_monday(self):
        when = services.next_digest_time('nove_ture')
        self.assertEqual(timezone.localtime(when).weekday(), 0)


class EventTests(NotificationBase):
    def test_waitlist_promotion(self):
        t = self.tour(self.A, max_participants=1)
        for u in (self.hiker, self.guideA2):
            self.login(u)
            self.call('post', 'api_tours:register', t.pk)
        self.login(self.hiker)
        reg = TourRegistration.objects.get(tour=t, user=self.hiker)
        self.call('post', 'api_me:cancel', reg.pk)
        self.assertTrue(self.rows(self.guideA2, 'lista_cekanja_mjesto').exists())
        self.assertTrue(self.rows(self.adminA, 'tura_popunjena').exists())

    def test_publish_notifies_members_and_guides_only(self):
        ClubMembership.objects.create(club=self.A, user=self.hiker, status=ClubMembership.Status.APPROVED)
        ClubMembership.objects.create(club=self.A, user=self.adminB, status=ClubMembership.Status.REJECTED)
        draft = self.tour(self.A, status=Tour.Status.DRAFT)
        self.login(self.adminA)
        self.assertEqual(self.call('post', 'api_manage:transition', self.A.pk, draft.pk, data={'action': 'publish'}).status_code, 200)
        self.assertTrue(self.rows(self.hiker, 'nova_tura').exists())
        self.assertFalse(self.rows(self.adminB, 'nova_tura').exists())
        self.assertEqual(set(Outbox.objects.filter(template='tura_bez_vodica').values_list('user', flat=True)),
                         {self.guideA.pk, self.guideA2.pk})

    def test_cancel_tour_notifies_participants(self):
        self.login(self.adminA)
        self.call('post', 'api_manage:transition', self.A.pk, self.tA.pk, data={'action': 'cancel'})
        self.assertTrue(self.rows(self.hiker, 'tura_otkazana').exists())
        self.assertTrue(self.rows(self.guideA, 'tura_otkazana').exists())

    def test_membership_and_club_flow(self):
        self.login(self.hiker)
        self.call('post', 'api_clubs:membership', self.A.pk)
        self.assertTrue(self.rows(self.adminA, 'clanstvo_zahtjev').exists())
        self.assertFalse(self.rows(self.adminB, 'clanstvo_zahtjev').exists())
        m = ClubMembership.objects.get(user=self.hiker)
        self.login(self.adminA)
        self.call('post', 'api_manage:member_decide', self.A.pk, m.pk, data={'decision': 'approve'})
        self.assertTrue(self.rows(self.hiker, 'clanstvo_odluka').get().context['approved'])

    def test_security_events(self):
        self.login(self.hiker)
        self.call('post', 'api_me:password', data={'oldPassword': PW, 'newPassword': 'Nova-Lozinka-Vrh-77',
                                                   'newPasswordConfirm': 'Nova-Lozinka-Vrh-77'})
        self.assertTrue(self.rows(self.hiker, 'lozinka_promijenjena').exists())
        self.login(self.sys)
        self.call('post', 'api_system:user_toggle', self.guideA2.pk)
        self.assertTrue(self.rows(self.guideA2, 'nalog_blokiran').exists())

    def test_lockout_email_at_most_once_per_hour(self):
        anon = Client(enforce_csrf_checks=False)
        for _ in range(12):        # dva zaključavanja zaredom
            anon.post(reverse('api_auth:login'), json.dumps({'email': self.adminB.email, 'password': 'x'}),
                      content_type='application/json')
            self.adminB.refresh_from_db()
            if self.adminB.locked_until:
                type(self.adminB).objects.filter(pk=self.adminB.pk).update(locked_until=None)
        self.assertEqual(self.rows(self.adminB, 'nalog_zakljucan').count(), 1)

    def test_duplicate_registration_notifies_owner_with_same_response(self):
        anon = Client()
        body = {'email': self.hiker.email, 'firstName': 'X', 'lastName': 'Y', 'phone': '',
                'password': 'Neka-Lozinka-Duga-9', 'passwordConfirm': 'Neka-Lozinka-Duga-9'}
        r = anon.post(reverse('api_auth:register'), json.dumps(body), content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(self.rows(self.hiker, 'registracija_postojeci').exists())


class UnsubscribeTests(NotificationBase):
    def test_one_click_without_csrf(self):
        token = services.unsubscribe_token(self.hiker, 'nove_ture')
        r = Client(enforce_csrf_checks=True).post(reverse('api_notifications:one_click', args=[token]),
                                                  {'List-Unsubscribe': 'One-Click'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(services.mode_for(self.hiker, 'nove_ture'), 'iskljuceno')
        self.assertEqual(Client().get(reverse('api_notifications:one_click', args=[token])).status_code, 405)

    def test_tampered_foreign_or_security_token_rejected(self):
        good = services.unsubscribe_token(self.hiker, 'nove_ture')
        for bad in [good[:-2] + 'xx', 'nesto', services.unsubscribe_token(self.hiker, 'sigurnost')]:
            r = Client().post(reverse('api_notifications:one_click', args=[bad]))
            self.assertEqual(r.status_code, 400, bad)
        self.assertEqual(services.mode_for(self.hiker, 'sigurnost'), 'odmah')

    def test_page_unsubscribe_and_headers(self):
        self.login(self.guideA2)
        self.call('post', 'api_tours:register', self.tour(self.A).pk)
        self.call('post', 'api_me:password', data={'oldPassword': PW, 'newPassword': 'Nova-Lozinka-Vrh-77',
                                                   'newPasswordConfirm': 'Nova-Lozinka-Vrh-77'})
        send()
        by_cat = {('Lozinka' in m.subject): m for m in mail.outbox}
        self.assertIn('List-Unsubscribe', by_cat[False].extra_headers)
        self.assertNotIn('List-Unsubscribe', by_cat[True].extra_headers)      # sigurnosni: bez odjave
        token = services.unsubscribe_token(self.guideA2, 'moje_ture')
        anon = Client(enforce_csrf_checks=True)
        anon.get(reverse('api_auth:csrf'))
        r = anon.post(reverse('api_notifications:unsubscribe'), json.dumps({'token': token}),
                      content_type='application/json', headers={'X-CSRFToken': anon.cookies['csrftoken'].value})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(services.mode_for(self.guideA2, 'moje_ture'), 'iskljuceno')


class SenderTests(NotificationBase):
    def row(self, user=None, **kw):
        return Outbox.objects.create(user=user or self.hiker, category='moje_ture', template='prijava_potvrda',
                                     context=services.tour_context(self.tA, waitlist=False, url='https://x/'), **kw)

    def test_retry_then_fail(self):
        r = self.row()
        now = timezone.now()
        with mock.patch('notifications.sender.EmailMultiAlternatives.send', side_effect=OSError('smtp')):
            for i in range(sender.MAX_ATTEMPTS):
                send(now)
                r.refresh_from_db()
                now = r.send_after + timedelta(seconds=1)
        self.assertEqual((r.status, r.attempts, r.last_error), (Outbox.Status.FAILED, sender.MAX_ATTEMPTS, 'OSError'))

    def test_rate_limit_defers(self):
        for _ in range(sender.MAX_PER_HOUR + 3):
            self.row()
        sent, deferred, _ = send()
        self.assertEqual((sent, deferred), (sender.MAX_PER_HOUR, 3))

    def test_expired_and_blocked_are_skipped(self):
        old = self.row(expires_at=timezone.now() - timedelta(minutes=1))
        type(self.hiker).objects.filter(pk=self.adminB.pk).update(is_active=False)
        self.adminB.refresh_from_db()
        blocked = self.row(user=self.adminB)
        sec = Outbox.objects.create(user=self.adminB, category='sigurnost', template='nalog_blokiran', context={})
        send()
        old.refresh_from_db(); blocked.refresh_from_db(); sec.refresh_from_db()
        self.assertEqual((old.status, blocked.status, sec.status),
                         (Outbox.Status.SKIPPED, Outbox.Status.SKIPPED, Outbox.Status.SENT))

    @override_settings(NOTIFICATIONS_ENABLED=False)
    def test_command_does_not_send_when_disabled(self):
        self.row()
        call_command('send_notifications', stdout=mock.MagicMock())
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(Outbox.objects.filter(status=Outbox.Status.PENDING).exists())

    def test_every_template_renders(self):
        from . import templates as tpl
        ctx = {**services.tour_context(self.tA), 'url': 'https://x/', 'name': 'Ime', 'action': 'Prijava',
               'action_lower': 'prijava', 'registered': 1, 'max': 2, 'approved': True, 'waitlist': False,
               'city': 'Grad', 'minutes': 15, 'equipment': ''}
        for name in tpl.SUBJECTS:
            self.assertTrue(tpl.subject(name, ctx))
            self.assertTrue(tpl.summary(name, ctx))
            self.assertIn('Zdravo', tpl.render_text(name, {**ctx, 'first_name': 'A', 'settings_url': 'https://x/'}))


class ScheduledTests(NotificationBase):
    def test_reminder_once_and_no_guide_warning(self):
        Tour.objects.filter(pk=self.tA.pk).update(start_at=timezone.now() + timedelta(hours=20),
                                                  registration_deadline=timezone.now() + timedelta(hours=10))
        TourGuide.objects.filter(tour=self.tA).delete()
        from .scheduled import schedule_due
        schedule_due()
        schedule_due()
        self.assertEqual(self.rows(self.hiker, 'podsjetnik').count(), 1)
        self.assertEqual(self.rows(self.adminA, 'tura_bez_vodica_upozorenje').count(), 1)
        self.assertFalse(self.rows(self.adminB, 'tura_bez_vodica_upozorenje').exists())

    def test_categories_are_consistent(self):
        for c in BY_CODE.values():
            self.assertIn(c.default, c.modes)
            if c.security:
                self.assertEqual(c.modes, ('odmah',))
