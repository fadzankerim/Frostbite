import json
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import AuditLog
from clubs.models import Club, ClubAdmin, ClubGuide, ClubMembership
from tours.models import Tour, TourGuide, TourRegistration

PW = 'Snijeg-Na-Bjelasnici-42'


class Base(TestCase):
    def setUp(self):
        mk = lambda e, f, **kw: User.objects.create_user(e, PW, first_name=f, last_name='Test', **kw)  # noqa: E731
        self.adminA, self.adminB = mk('a@a.ba', 'AdminA'), mk('b@b.ba', 'AdminB')
        self.guideA, self.guideA2 = mk('g@a.ba', 'VodicA'), mk('g2@a.ba', 'VodicA2')
        self.hiker = mk('h@p.ba', 'Planinar', phone='061 999 888', health_notes='TAJNA-DIJAGNOZA',
                        emergency_contact_name='Mama', emergency_contact_phone='062 777 666')
        self.sys = User.objects.create_system_admin('s@f.ba', PW, first_name='Sys', last_name='Admin')
        self.A = Club.objects.create(name='PD A', city='X', status=Club.Status.APPROVED, created_by=self.adminA)
        self.B = Club.objects.create(name='PD B', city='Y', status=Club.Status.APPROVED, created_by=self.adminB)
        ClubAdmin.objects.create(club=self.A, user=self.adminA)
        ClubAdmin.objects.create(club=self.B, user=self.adminB)
        ClubGuide.objects.create(club=self.A, user=self.guideA)
        ClubGuide.objects.create(club=self.A, user=self.guideA2)
        self.tA = self.tour(self.A)
        self.tB = self.tour(self.B)
        TourGuide.objects.create(tour=self.tA, user=self.guideA, status=TourGuide.Status.APPROVED)
        self.reg = TourRegistration.objects.create(tour=self.tA, user=self.hiker)

    def tour(self, club, days=5, **kw):
        now = timezone.now()
        data = dict(club=club, name=f'Tura {club.name}', start_at=now + timedelta(days=days),
                    registration_deadline=now + timedelta(days=days - 1), meeting_point='M',
                    difficulty=Tour.Difficulty.EASY, length_km=5, elevation_gain_m=100, duration_h=2,
                    max_participants=10, status=Tour.Status.PUBLISHED, created_by=club.created_by)
        data.update(kw)
        return Tour.objects.create(**data)

    def as_(self, user):
        self.client.force_login(user)


class ClubAdminIsolationTests(Base):
    """Ograničenje 2: admin društva A nema nikakav pristup društvu B."""

    def test_other_club_dashboard_404(self):
        self.as_(self.adminA)
        self.assertEqual(self.client.get(reverse('panel:club', args=[self.A.pk])).status_code, 200)
        for name, args in [('panel:club', [self.B.pk]), ('panel:club_tours', [self.B.pk]), ('panel:members', [self.B.pk]), ('panel:guides', [self.B.pk]),
                           ('panel:club_profile', [self.B.pk]), ('panel:tour_create', [self.B.pk]),
                           ('panel:club_tour', [self.B.pk, self.tB.pk]), ('panel:tour_edit', [self.B.pk, self.tB.pk])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 404, name)

    def test_cannot_reach_other_club_tour_through_own_club_url(self):
        """IDOR: tura društva B preko URL-a društva A."""
        self.as_(self.adminA)
        self.assertEqual(self.client.get(reverse('panel:club_tour', args=[self.A.pk, self.tB.pk])).status_code, 404)
        r = self.client.post(reverse('panel:tour_transition', args=[self.A.pk, self.tB.pk, 'cancel']))
        self.assertEqual(r.status_code, 404)
        self.tB.refresh_from_db()
        self.assertEqual(self.tB.status, Tour.Status.PUBLISHED)

    def test_hiker_and_guide_cannot_access_admin(self):
        for u in [self.hiker, self.guideA, self.sys]:
            self.as_(u)
            self.assertEqual(self.client.get(reverse('panel:club', args=[self.A.pk])).status_code, 404)

    def test_suspended_club_admin_loses_access(self):
        Club.objects.filter(pk=self.A.pk).update(status=Club.Status.SUSPENDED)
        self.as_(self.adminA)
        self.assertEqual(self.client.get(reverse('panel:club', args=[self.A.pk])).status_code, 404)

    def test_registrations_view_hides_personal_data(self):
        """F27: admin vidi ime, prezime i status - ne telefon ni zdravstvene napomene."""
        self.as_(self.adminA)
        r = self.client.get(reverse('panel:club_tour', args=[self.A.pk, self.tA.pk]))
        self.assertContains(r, 'Planinar')
        self.assertNotContains(r, 'TAJNA-DIJAGNOZA')
        self.assertNotContains(r, '061 999 888')
        self.assertNotContains(r, 'h@p.ba')


class TourManagementTests(Base):
    def form(self, **over):
        now = timezone.localtime() + timedelta(days=10)
        data = {'name': 'Nova', 'region': 'R', 'description': '', 'start_at': now.strftime('%Y-%m-%dT%H:%M'),
                'registration_deadline': (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
                'meeting_point': 'M', 'difficulty': 'LAKA', 'length_km': '5', 'elevation_gain_m': '100',
                'duration_h': '2', 'max_participants': '10', 'price': '0', 'required_equipment': '',
                'route': json.dumps([[43.7, 18.2], [43.71, 18.21]])}
        data.update(over)
        return data

    def test_create_tour_is_draft_in_own_club(self):
        self.as_(self.adminA)
        self.client.post(reverse('panel:tour_create', args=[self.A.pk]),
                         self.form(status='OBJAVLJENA', club=self.B.pk))           # podmetanje polja
        t = Tour.objects.get(name='Nova')
        self.assertEqual(t.club, self.A)
        self.assertEqual(t.status, Tour.Status.DRAFT)
        self.assertEqual(t.route, [[43.7, 18.2], [43.71, 18.21]])

    def test_invalid_route_rejected(self):
        self.as_(self.adminA)
        for bad in ['nije json', json.dumps([[200, 18], [43, 18]]), json.dumps([['<b>', 1], [43, 18]]),
                    json.dumps({'a': 1}), json.dumps([[43, 18]] * 501), '[[NaN, 1], [43, 18]]']:
            r = self.client.post(reverse('panel:tour_create', args=[self.A.pk]), self.form(route=bad))
            self.assertEqual(r.status_code, 200, bad[:30])
        self.assertFalse(Tour.objects.filter(name='Nova').exists())

    def test_deadline_after_start_rejected(self):
        self.as_(self.adminA)
        now = timezone.localtime() + timedelta(days=10)
        self.client.post(reverse('panel:tour_create', args=[self.A.pk]), self.form(
            registration_deadline=(now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')))
        self.assertFalse(Tour.objects.filter(name='Nova').exists())

    def test_cannot_lower_capacity_below_registered(self):
        self.as_(self.adminA)
        TourRegistration.objects.create(tour=self.tA, user=self.guideA2)
        self.client.post(reverse('panel:tour_edit', args=[self.A.pk, self.tA.pk]), self.form(max_participants='1'))
        self.tA.refresh_from_db()
        self.assertEqual(self.tA.max_participants, 10)

    def test_done_and_cancelled_tours_locked(self):
        self.as_(self.adminA)
        for st in [Tour.Status.DONE, Tour.Status.CANCELLED]:
            Tour.objects.filter(pk=self.tA.pk).update(status=st)
            self.client.post(reverse('panel:tour_edit', args=[self.A.pk, self.tA.pk]), self.form(name='Promijenjeno'))
            self.tA.refresh_from_db()
            self.assertNotEqual(self.tA.name, 'Promijenjeno')

    def test_status_transitions(self):
        self.as_(self.adminA)
        draft = self.tour(self.A, status=Tour.Status.DRAFT)
        url = lambda a: reverse('panel:tour_transition', args=[self.A.pk, draft.pk, a])  # noqa: E731
        self.client.post(url('cancel'))                                   # NACRT -> OTKAZANA nije dozvoljeno
        draft.refresh_from_db(); self.assertEqual(draft.status, Tour.Status.DRAFT)
        self.client.post(url('publish'))
        draft.refresh_from_db(); self.assertEqual(draft.status, Tour.Status.PUBLISHED)
        self.client.post(url('cancel'))
        draft.refresh_from_db(); self.assertEqual(draft.status, Tour.Status.CANCELLED)
        self.client.post(url('publish'))                                  # otkazana se ne može ponovo objaviti
        draft.refresh_from_db(); self.assertEqual(draft.status, Tour.Status.CANCELLED)
        self.assertEqual(self.client.post(url('obrisi')).status_code, 404)
        self.assertEqual(self.client.get(url('publish')).status_code, 405)

    def test_membership_approval(self):
        m = ClubMembership.objects.create(club=self.A, user=self.hiker)
        self.as_(self.adminB)
        self.assertEqual(self.client.post(reverse('panel:membership_decide', args=[self.B.pk, m.pk, 'approve'])).status_code, 404)
        self.as_(self.adminA)
        self.client.post(reverse('panel:membership_decide', args=[self.A.pk, m.pk, 'approve']))
        m.refresh_from_db()
        self.assertEqual(m.status, 'ODOBRENO')
        self.assertEqual(m.valid_until.month, 12)
        self.assertEqual(m.decided_by, self.adminA)

    def test_add_guide_generic_message(self):
        self.as_(self.adminA)
        a = self.client.post(reverse('panel:guides', args=[self.A.pk]), {'email': 'h@p.ba'}, follow=True)
        b = self.client.post(reverse('panel:guides', args=[self.A.pk]), {'email': 'nema@nikoga.ba'}, follow=True)
        self.assertEqual([str(m) for m in a.context['messages']], [str(m) for m in b.context['messages']])
        self.assertTrue(ClubGuide.objects.filter(club=self.A, user=self.hiker, is_active=True).exists())

    def test_cannot_add_sysadmin_as_guide(self):
        self.as_(self.adminA)
        self.client.post(reverse('panel:guides', args=[self.A.pk]), {'email': 's@f.ba'})
        self.assertFalse(ClubGuide.objects.filter(user=self.sys).exists())

    def test_guide_decision(self):
        app = TourGuide.objects.create(tour=self.tA, user=self.guideA2)
        self.as_(self.adminA)
        self.assertEqual(self.client.post(reverse('panel:guide_decide', args=[self.A.pk, self.tA.pk, app.pk, 'x'])).status_code, 404)
        self.client.post(reverse('panel:guide_decide', args=[self.A.pk, self.tA.pk, app.pk, 'approve']))
        app.refresh_from_db()
        self.assertEqual(app.status, TourGuide.Status.APPROVED)


class GuideTests(Base):
    def test_approved_guide_sees_personal_data_and_access_is_logged(self):
        self.as_(self.guideA)
        r = self.client.get(reverse('panel:guide_tour', args=[self.tA.pk]))
        self.assertContains(r, 'TAJNA-DIJAGNOZA')
        self.assertContains(r, '062 777 666')
        self.assertTrue(AuditLog.objects.filter(action='PRISTUP_LICNIM_PODACIMA', user=self.guideA).exists())

    def test_other_guide_of_same_club_cannot(self):
        self.as_(self.guideA2)
        self.assertEqual(self.client.get(reverse('panel:guide_tour', args=[self.tA.pk])).status_code, 404)

    def test_applied_but_not_approved_cannot(self):
        TourGuide.objects.create(tour=self.tB, user=self.guideA2)
        self.as_(self.guideA2)
        self.assertEqual(self.client.get(reverse('panel:guide_tour', args=[self.tB.pk])).status_code, 404)

    def test_removed_guide_loses_access(self):
        ClubGuide.objects.filter(user=self.guideA).update(is_active=False)
        self.as_(self.guideA)
        self.assertEqual(self.client.get(reverse('panel:guide_tour', args=[self.tA.pk])).status_code, 403)

    def test_access_window_closes_7_days_after_tour(self):
        Tour.objects.filter(pk=self.tA.pk).update(start_at=timezone.now() - timedelta(days=8),
                                                  registration_deadline=timezone.now() - timedelta(days=9))
        self.as_(self.guideA)
        self.assertEqual(self.client.get(reverse('panel:guide_tour', args=[self.tA.pk])).status_code, 404)

    def test_admin_and_hiker_cannot_see_participants(self):
        for u in [self.adminA, self.hiker, self.sys]:
            self.as_(u)
            self.assertIn(self.client.get(reverse('panel:guide_tour', args=[self.tA.pk])).status_code, (403, 404))

    def test_guide_can_apply_only_in_own_club(self):
        self.as_(self.guideA2)
        self.assertEqual(self.client.post(reverse('panel:guide_apply', args=[self.tB.pk])).status_code, 404)
        tA2 = self.tour(self.A, name='Druga')
        self.client.post(reverse('panel:guide_apply', args=[tA2.pk]))
        self.assertTrue(TourGuide.objects.filter(tour=tA2, user=self.guideA2, status='PRIJAVIO_SE').exists())

    def test_attendance_and_report(self):
        Tour.objects.filter(pk=self.tA.pk).update(start_at=timezone.now() - timedelta(hours=2),
                                                  registration_deadline=timezone.now() - timedelta(days=1),
                                                  status=Tour.Status.CLOSED)
        other = TourRegistration.objects.create(tour=self.tB, user=self.guideA2)    # tuđa prijava
        self.as_(self.guideA)
        self.client.post(reverse('panel:guide_attendance', args=[self.tA.pk]), {'present': [self.reg.pk, other.pk, 'x']})
        self.reg.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(self.reg.attendance, 'PRISUSTVOVAO')
        self.assertEqual(other.attendance, '')                       # tuđa tura netaknuta
        self.client.post(reverse('panel:guide_report', args=[self.tA.pk]), {'text': 'Sve u redu.'})
        self.tA.refresh_from_db()
        self.assertEqual(self.tA.status, Tour.Status.DONE)
        self.assertEqual(self.tA.report.attendees_count, 1)

    def test_attendance_not_before_tour_day(self):
        self.as_(self.guideA)
        self.client.post(reverse('panel:guide_attendance', args=[self.tA.pk]), {'present': [self.reg.pk]})
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.attendance, '')


class SystemAdminTests(Base):
    def test_only_sysadmin(self):
        for u in [self.hiker, self.adminA, self.guideA]:
            self.as_(u)
            for name in ['panel:sys_clubs', 'panel:sys_users', 'panel:sys_audit']:
                self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('panel:sys_audit')).status_code, 302)

    def test_approve_pending_club_gives_admin_rights(self):
        pending = Club.objects.create(name='PD Novo', city='Z', created_by=self.hiker)
        ClubAdmin.objects.create(club=pending, user=self.hiker)
        self.as_(self.sys)
        self.client.post(reverse('panel:sys_club_decide', args=[pending.pk, 'approve']))
        pending.refresh_from_db()
        self.assertEqual(pending.status, Club.Status.APPROVED)
        self.as_(self.hiker)
        self.assertEqual(self.client.get(reverse('panel:club', args=[pending.pk])).status_code, 200)

    def test_block_user_kills_session_and_not_self(self):
        self.client.force_login(self.hiker)
        hiker_session = self.client.session.session_key
        self.client.logout()
        from django.test import Client
        c = Client(); c.force_login(self.hiker)
        self.as_(self.sys)
        self.client.post(reverse('panel:sys_user_toggle', args=[self.hiker.pk]))
        self.hiker.refresh_from_db()
        self.assertFalse(self.hiker.is_active)
        self.assertEqual(c.get(reverse('accounts:profile')).status_code, 302)
        self.assertFalse(Session.objects.filter(session_key=hiker_session).exists())
        self.client.post(reverse('panel:sys_user_toggle', args=[self.sys.pk]))
        self.sys.refresh_from_db()
        self.assertTrue(self.sys.is_active)

    def test_users_list_hides_sensitive_fields(self):
        self.as_(self.sys)
        r = self.client.get(reverse('panel:sys_users'))
        self.assertContains(r, 'h@p.ba')
        self.assertNotContains(r, 'TAJNA-DIJAGNOZA')
        self.assertNotContains(r, '061 999 888')

    def test_audit_log_readable(self):
        AuditLog.objects.create(action='TEST_AKCIJA')
        self.as_(self.sys)
        self.assertContains(self.client.get(reverse('panel:sys_audit') + '?action=TEST'), 'TEST_AKCIJA')


class LandingAndAnalyticsTests(Base):
    def login(self, email):
        return self.client.post(reverse('accounts:login'), {'username': email, 'password': PW})

    def test_role_landing_pages(self):
        self.assertRedirects(self.login('s@f.ba'), reverse('panel:sys_dashboard'))
        self.client.logout()
        r = self.login('a@a.ba')
        self.assertRedirects(r, reverse('panel:club_choose'), target_status_code=302)
        self.client.logout()
        self.assertRedirects(self.login('g@a.ba'), reverse('panel:guide'))
        self.client.logout()
        self.assertRedirects(self.login('h@p.ba'), reverse('home'))

    def test_next_param_still_wins_but_stays_local(self):
        r = self.client.post(reverse('accounts:login') + '?next=/drustva/', {'username': 's@f.ba', 'password': PW})
        self.assertRedirects(r, '/drustva/')
        self.client.logout()
        r = self.client.post(reverse('accounts:login') + '?next=//zlo.example/', {'username': 's@f.ba', 'password': PW})
        self.assertRedirects(r, reverse('panel:sys_dashboard'))

    def test_dashboards_access(self):
        self.as_(self.sys)
        self.assertEqual(self.client.get(reverse('panel:sys_dashboard')).status_code, 200)
        for u in [self.adminA, self.guideA, self.hiker]:
            self.as_(u)
            self.assertEqual(self.client.get(reverse('panel:sys_dashboard')).status_code, 403)
        self.as_(self.adminA)
        r = self.client.get(reverse('panel:club', args=[self.A.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'TAJNA-DIJAGNOZA')
        self.assertEqual(self.client.get(reverse('panel:club', args=[self.B.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('panel:club_tours', args=[self.B.pk])).status_code, 404)

    def test_sys_dashboard_has_no_personal_data(self):
        self.as_(self.sys)
        r = self.client.get(reverse('panel:sys_dashboard'))
        self.assertNotContains(r, 'TAJNA-DIJAGNOZA')
        self.assertNotContains(r, '061 999 888')

    def test_revenue_counts_present_only(self):
        done = self.tour(self.A, days=-3, registration_deadline=timezone.now() - timedelta(days=4),
                         status=Tour.Status.DONE, price=10)
        TourRegistration.objects.create(tour=done, user=self.hiker, attendance='PRISUSTVOVAO')
        TourRegistration.objects.create(tour=done, user=self.guideA2, attendance='NIJE_DOSAO')
        self.as_(self.adminA)
        r = self.client.get(reverse('panel:club', args=[self.A.pk]))
        self.assertEqual(r.context['money']['earned'], 10.0)
        self.assertEqual(r.context['phases']['done'], 1)


class GuideAssignTests(Base):
    def assign(self, club, tour, guide_pk):
        return self.client.post(reverse('panel:guide_assign', args=[club.pk, tour.pk]), {'guide': guide_pk})

    def test_admin_assigns_own_club_guide(self):
        g2 = ClubGuide.objects.get(user=self.guideA2)
        t = self.tour(self.A, name='Bez vodiča')
        self.as_(self.adminA)
        self.assign(self.A, t, g2.pk)
        self.assertTrue(TourGuide.objects.filter(tour=t, user=self.guideA2, status='ODOBREN').exists())
        self.assertTrue(AuditLog.objects.filter(action='VODIC_DODIJELJEN').exists())

    def test_cannot_assign_guide_of_other_club_or_to_other_club(self):
        gB = ClubGuide.objects.create(club=self.B, user=User.objects.create_user('gb@b.ba', PW, first_name='GB', last_name='T'))
        t = self.tour(self.A, name='Bez vodiča')
        self.as_(self.adminA)
        self.assertEqual(self.assign(self.A, t, gB.pk).status_code, 404)
        self.assertEqual(self.assign(self.A, self.tB, ClubGuide.objects.get(user=self.guideA2).pk).status_code, 404)
        self.assertEqual(self.assign(self.A, t, 'abc').status_code, 404)
        self.as_(self.adminB)
        self.assertEqual(self.assign(self.A, t, gB.pk).status_code, 404)
        self.assertFalse(TourGuide.objects.filter(tour=t).exists())

    def test_cannot_assign_participant_or_to_finished_tour(self):
        g2 = ClubGuide.objects.get(user=self.guideA2)
        TourRegistration.objects.create(tour=self.tA, user=self.guideA2)
        self.as_(self.adminA)
        self.assign(self.A, self.tA, g2.pk)
        self.assertFalse(TourGuide.objects.filter(tour=self.tA, user=self.guideA2).exists())
        Tour.objects.filter(pk=self.tA.pk).update(status=Tour.Status.CANCELLED)
        TourRegistration.objects.filter(user=self.guideA2).update(status='ODJAVLJEN')
        self.assign(self.A, self.tA, g2.pk)
        self.assertFalse(TourGuide.objects.filter(tour=self.tA, user=self.guideA2).exists())
