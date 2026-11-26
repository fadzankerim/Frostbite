"""API panela sistemskog admina (/api/system/). Pravila su u panel.system_service.

Samo sistemski admin (ostali 403). Podaci o korisnicima: ime, prezime, email i status -
nikad telefon, hitni kontakt ni zdravstvene napomene (politika 4.5). Evidencija je samo za čitanje.
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from frostbite.api import ApiView

from . import system_service as svc

MAX_QUERY = 100


class IsSystemAdmin(BasePermission):
    message = 'Ova radnja nije dozvoljena.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_system_admin)


def _page_number(request):
    raw = request.query_params.get('page', '1')
    return int(raw) if raw.isdigit() and 0 < int(raw) < 100000 else 1


def _page_meta(page):
    return {'page': page.number, 'pages': page.paginator.num_pages, 'total': page.paginator.count}


def _series(items):
    return [{'label': label, 'value': value} for label, value in items]


class SystemView(ApiView):
    permission_classes = [IsSystemAdmin]


class DashboardView(SystemView):
    def get(self, request):
        d = svc.dashboard()
        return Response({
            'kpi': {'users': d['kpi']['users'], 'newUsers': d['kpi']['new_users'], 'clubs': d['kpi']['clubs'],
                    'pendingClubs': d['kpi']['pending_clubs'], 'toursActive': d['kpi']['tours_active'],
                    'registrations': d['kpi']['registrations']},
            'security': {'failed': d['sec']['failed'], 'lockouts': d['sec']['lockouts'], 'lockedNow': d['sec']['locked_now'],
                         'blocked': d['sec']['blocked'], 'personalDataAccess': d['sec']['pii']},
            'logins': _series(d['logins']),
            'fails': _series(d['fails']),
            'tourStatus': [{'label': str(label), 'count': c} for label, c in d['tour_status']],
            'pendingClubs': [{'id': c.pk, 'name': c.name, 'city': c.city, 'createdAt': c.created_at.isoformat()}
                             for c in d['pending_clubs']],
            'events': [{'id': e.pk, 'action': e.action, 'createdAt': e.created_at.isoformat(), 'ip': e.ip,
                        'details': e.details, 'user': e.user.email if e.user else None} for e in d['events']],
        })


def _club(c):
    return {
        'id': c.pk, 'name': c.name, 'city': c.city, 'createdAt': c.created_at.isoformat(),
        'status': {'code': c.status, 'label': c.get_status_display()},
        'createdBy': {'name': c.created_by.get_full_name(), 'email': c.created_by.email},
        'actions': svc.available_club_actions(c),
    }


class ClubsView(SystemView):
    def get(self, request):
        pending, others = svc.clubs()
        return Response({'pending': [_club(c) for c in pending], 'others': [_club(c) for c in others]})


class ClubDecideView(SystemView):
    def post(self, request, pk):
        action = request.data.get('action') if isinstance(request.data, dict) else None
        try:
            club = svc.decide_club(request._request, pk, action if isinstance(action, str) else '')
        except svc.AdminActionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': f'Društvo „{club.name}“: {club.get_status_display().lower()}.'})


class UsersView(SystemView):
    def get(self, request):
        q = request.query_params.get('q', '').strip()[:MAX_QUERY]
        page = svc.users_page(q, _page_number(request))
        now = timezone.now()
        return Response({**_page_meta(page), 'results': [{
            'id': u.pk, 'email': u.email, 'firstName': u.first_name, 'lastName': u.last_name,
            'isActive': u.is_active, 'isSystemAdmin': u.is_system_admin,
            'dateJoined': u.date_joined.isoformat(), 'locked': bool(u.locked_until and u.locked_until > now),
            'isSelf': u.pk == request.user.pk,
        } for u in page.object_list]})


class UserToggleView(SystemView):
    def post(self, request, pk):
        try:
            target = svc.toggle_user(request._request, pk)
        except svc.AdminActionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': f'Nalog {target.email} je {"deblokiran" if target.is_active else "blokiran"}.',
                         'isActive': target.is_active})


class AuditView(SystemView):
    def get(self, request):
        action = request.query_params.get('action', '').strip()[:50]
        page = svc.audit_page(action, _page_number(request))
        return Response({**_page_meta(page), 'results': [{
            'id': e.pk, 'action': e.action, 'entity': e.entity, 'entityId': e.entity_id, 'details': e.details,
            'ip': e.ip, 'createdAt': e.created_at.isoformat(), 'user': e.user.email if e.user else None,
        } for e in page.object_list]})
