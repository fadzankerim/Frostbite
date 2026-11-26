"""API panela vodiča (/api/guide/). Pravila su u panel.guide_service.

Lični podaci učesnika (telefon, hitni kontakt, zdravstvene napomene) izlaze SAMO odobrenom
vodiču te ture, najviše 7 dana nakon ture, i svaki pristup se bilježi (PRISTUP_LICNIM_PODACIMA).
Tuđe ture daju 404, isto kao nepostojeće.
"""
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from accounts.permissions import is_guide
from frostbite.api import ApiView
from tours.models import Tour

from . import guide_service as svc


class IsGuide(BasePermission):
    """Aktivan vodič u barem jednom odobrenom društvu (isto kao guide_required)."""
    message = 'Ova radnja nije dozvoljena.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and is_guide(u))


def _tour_brief(t):
    start = t.route[0] if isinstance(t.route, list) and len(t.route) >= 2 else None
    return {
        'id': t.pk, 'name': t.name, 'startAt': t.start_at.isoformat(),
        'club': {'id': t.club_id, 'name': t.club.name},
        'status': {'code': t.status, 'label': t.get_status_display()},
        'difficulty': {'code': t.difficulty, 'label': t.get_difficulty_display()},
        'meetingPoint': t.meeting_point,
        'start': [float(start[0]), float(start[1])] if start else None,
    }


def _err(e, code=status.HTTP_400_BAD_REQUEST):
    body = {'detail': str(e)}
    if getattr(e, 'errors', None):
        body['errors'] = {k: [x['message'] for x in v] for k, v in e.errors.items()}
    return Response(body, status=code)


class GuideDashboardView(ApiView):
    """F15 - ture bez vodiča (za prijavu) i ture koje korisnik vodi."""
    permission_classes = [IsGuide]

    def get(self, request):
        return Response({
            'openTours': [{**_tour_brief(t), 'applied': t.applied} for t in svc.open_tours(request.user)],
            'myTours': [_tour_brief(t) for t in svc.my_tours(request.user)],
        })


class GuideApplyView(ApiView):
    """F16 - prijava za vođenje ture vlastitog društva."""
    permission_classes = [IsGuide]

    def post(self, request, pk):
        try:
            svc.apply(request._request, pk)
        except svc.GuideError as e:
            return _err(e)
        return Response({'detail': 'Prijava za vođenje je poslana adminu društva.'}, status=status.HTTP_201_CREATED)


class GuideTourView(ApiView):
    """F17 - tura koju korisnik vodi, sa učesnicima i ličnim podacima (pristup se bilježi)."""
    permission_classes = [IsGuide]

    def get(self, request, pk):
        tour, regs, report = svc.participants(request._request, pk)
        attendance_open = svc.attendance_open(tour)
        active = tour.status in (Tour.Status.PUBLISHED, Tour.Status.CLOSED)
        return Response({
            **_tour_brief(tour),
            'maxParticipants': tour.max_participants,
            'canClose': tour.status == Tour.Status.PUBLISHED,
            'attendanceOpen': attendance_open and active,
            'canReport': attendance_open and active and report is None,
            'report': {'text': report.text, 'attendeesCount': report.attendees_count,
                       'createdAt': report.created_at.isoformat()} if report else None,
            'participants': [{
                'id': r.pk,
                'name': r.user.get_full_name(),
                'phone': r.user.phone,
                'emergencyContactName': r.user.emergency_contact_name,
                'emergencyContactPhone': r.user.emergency_contact_phone,
                'healthNotes': r.user.health_notes,
                'status': {'code': r.status, 'label': r.get_status_display()},
                'attendance': r.attendance or None,
            } for r in regs],
        })


class GuideCloseView(ApiView):
    """F18 - zatvaranje prijava."""
    permission_classes = [IsGuide]

    def post(self, request, pk):
        try:
            svc.close_registrations(request._request, pk)
        except svc.GuideError as e:
            return _err(e)
        return Response({'detail': 'Prijave su zatvorene.'})


class GuideAttendanceView(ApiView):
    """F19 - prisustvo: {"present": [id prijave, ...]}; svi ostali prijavljeni su odsutni."""
    permission_classes = [IsGuide]

    def post(self, request, pk):
        raw = request.data.get('present') if isinstance(request.data, dict) else None
        if not isinstance(raw, list) or len(raw) > 1000 or \
                not all(isinstance(x, int) and not isinstance(x, bool) for x in raw):
            return Response({'detail': 'Neispravan spisak prisutnih.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = svc.save_attendance(request._request, pk, set(raw))
        except svc.GuideError as e:
            return _err(e)
        return Response({'detail': 'Prisustvo je sačuvano.', 'present': count})


class GuideReportView(ApiView):
    """F20 - izvještaj sa ture: {"text": "..."}; tura postaje ODRŽANA."""
    permission_classes = [IsGuide]

    def post(self, request, pk):
        text = request.data.get('text') if isinstance(request.data, dict) else None
        try:
            svc.save_report(request._request, pk, {'text': text if isinstance(text, str) else ''})
        except svc.GuideError as e:
            return _err(e)
        return Response({'detail': 'Izvještaj je sačuvan, a tura je označena kao održana.'}, status=status.HTTP_201_CREATED)
