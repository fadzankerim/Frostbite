"""API panela admina društva (/api/manage/<club_id>/...). Pravila su u panel.club_service.

Društvo iz URL-a se traži SAMO među društvima kojima korisnik upravlja (admin_clubs) - tuđe
društvo daje 404, isto kao nepostojeće. Unutar društva se svaka tura, vodič i članstvo traže
kroz to društvo (IDOR zaštita). Admin vidi samo ime, prezime i status učesnika (F27) - bez
kontakta i zdravstvenih podataka.
"""
import json

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from accounts.permissions import admin_clubs
from frostbite.api import ApiView, form_errors

from . import club_service as svc
from .forms import DT_FORMAT, AddGuideForm, ClubProfileForm, TourForm


def _local(dt):
    return timezone.localtime(dt).strftime(DT_FORMAT)


def _err(e):
    return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClubAdminView(ApiView):
    """Bazni view: self.club = društvo kojim korisnik upravlja (inače 404)."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if 'club_pk' in kwargs:
            self.club = get_object_or_404(admin_clubs(request.user), pk=kwargs['club_pk'])


def _body(request):
    return request.data if isinstance(request.data, dict) else {}


class ManagedClubsView(ClubAdminView):
    def get(self, request):
        return Response({'results': [{'id': c.pk, 'name': c.name, 'city': c.city}
                                     for c in admin_clubs(request.user).order_by('name')]})


def _tour_row(t):
    return {
        'id': t.pk, 'name': t.name, 'startAt': t.start_at.isoformat(),
        'status': {'code': t.status, 'label': t.get_status_display()},
        'difficulty': {'code': t.difficulty, 'label': t.get_difficulty_display()},
        'maxParticipants': t.max_participants,
        'taken': getattr(t, 'taken', None), 'waiting': getattr(t, 'waiting', None),
        'guideApps': getattr(t, 'guide_apps', None),
    }


class DashboardView(ClubAdminView):
    def get(self, request, club_pk):
        d = svc.dashboard(self.club)
        c = self.club
        return Response({
            'club': {'id': c.pk, 'name': c.name, 'city': c.city},
            'phases': d['phases'], 'money': d['money'], 'fill': d['fill'],
            'guides': [{'name': n, 'led': k} for n, k in d['guide_rows']],
            'membersCount': d['members_count'],
            'pendingMembers': d['pending_members'],
            'pendingGuides': d['pending_guides'],
            'unguided': [_tour_row(t) for t in d['unguided']],
            'upcoming': [_tour_row(t) for t in d['active'][:6]],
            'months': [{'label': label, 'people': p, 'money': m} for label, p, m in d['months']],
        })


class ProfileView(ClubAdminView):
    """F21 - profil društva. Naziv i status mijenja samo sistemski admin."""
    FIELDS = ['city', 'description', 'email', 'phone']

    def payload(self):
        c = self.club
        return {'name': c.name, **{f: getattr(c, f) for f in self.FIELDS}}

    def get(self, request, club_pk):
        return Response(self.payload())

    def put(self, request, club_pk):
        d = _body(request)
        form = ClubProfileForm({f: d.get(f) if isinstance(d.get(f), str) else '' for f in self.FIELDS}, instance=self.club)
        if not form.is_valid():
            return Response({'errors': form_errors(form)}, status=status.HTTP_400_BAD_REQUEST)
        svc.save_profile(request._request, self.club, form)
        return Response({**self.payload(), 'detail': 'Profil društva je sačuvan.'})


class GuidesView(ClubAdminView):
    """F22 - vodiči društva; dodavanje po emailu uvijek daje istu poruku (bez otkrivanja naloga)."""

    def get(self, request, club_pk):
        return Response({'results': [{'id': g.pk, 'name': g.user.get_full_name(),
                                      'licenseNumber': g.license_number, 'since': g.added_at.isoformat()}
                                     for g in svc.club_guides(self.club)]})

    def post(self, request, club_pk):
        d = _body(request)
        form = AddGuideForm({'email': d.get('email', ''), 'license_number': d.get('licenseNumber', '')})
        if not form.is_valid():
            errors = form_errors(form)
            return Response({'errors': {'licenseNumber' if k == 'license_number' else k: v for k, v in errors.items()}},
                            status=status.HTTP_400_BAD_REQUEST)
        svc.add_guide(request._request, self.club, form.cleaned_data['email'], form.cleaned_data['license_number'])
        return Response({'detail': svc.ADD_GUIDE_MSG})


class GuideRemoveView(ClubAdminView):
    def post(self, request, club_pk, pk):
        g = svc.remove_guide(request._request, self.club, pk)
        return Response({'detail': f'{g.user.get_full_name()} više nije vodič društva.'})


_TOUR_FIELDS = {  # API ime -> polje TourForm
    'name': 'name', 'region': 'region', 'description': 'description', 'startAt': 'start_at',
    'registrationDeadline': 'registration_deadline', 'meetingPoint': 'meeting_point', 'difficulty': 'difficulty',
    'lengthKm': 'length_km', 'elevationGainM': 'elevation_gain_m', 'durationH': 'duration_h',
    'maxParticipants': 'max_participants', 'price': 'price', 'membersOnly': 'members_only',
    'requiredEquipment': 'required_equipment',
}
_FORM_TO_API = {v: k for k, v in _TOUR_FIELDS.items()}


def _tour_form(request, instance=None):
    """JSON -> TourForm. Vrijednosti se predaju kao tekst (kao iz HTML forme); validira ih forma.
    Polja koja nisu u _TOUR_FIELDS (status, club, created_by...) se ignorišu."""
    d = _body(request)
    data = {}
    for api_name, field in _TOUR_FIELDS.items():
        v = d.get(api_name)
        if field == 'members_only':
            if v is True:
                data[field] = 'on'
        elif isinstance(v, bool) or v is None:
            data[field] = ''
        elif isinstance(v, (int, float, str)):
            data[field] = str(v)
    route = d.get('route', [])
    data['route'] = json.dumps(route) if isinstance(route, list) else 'x'     # 'x' -> greška validacije
    return TourForm(data, instance=instance)


def _form_error_response(form):
    return Response({'errors': {_FORM_TO_API.get(k, k): v for k, v in form_errors(form).items()}},
                    status=status.HTTP_400_BAD_REQUEST)


class ToursView(ClubAdminView):
    """F23 - lista i kreiranje (uvijek NACRT, u ovom društvu)."""

    def get(self, request, club_pk):
        upcoming, past = svc.tours_overview(self.club)
        return Response({'upcoming': [_tour_row(t) for t in upcoming], 'past': [_tour_row(t) for t in past]})

    def post(self, request, club_pk):
        form = _tour_form(request)
        if not form.is_valid():
            return _form_error_response(form)
        tour = svc.create_tour(request._request, self.club, form)
        return Response({'id': tour.pk, 'detail': 'Tura je sačuvana kao nacrt. Objavite je kada bude spremna.'},
                        status=status.HTTP_201_CREATED)


class TourView(ClubAdminView):
    """F23-F25, F27 - detalji ture za admina (bez ličnih podataka učesnika) i izmjena."""

    def get(self, request, club_pk, pk):
        t, regs, apps, assignable = svc.tour_detail(self.club, pk)
        return Response({
            **_tour_row(t),
            'editable': t.status in svc.EDITABLE,
            'transitions': svc.available_transitions(t),
            'form': {
                'name': t.name, 'region': t.region, 'description': t.description,
                'startAt': _local(t.start_at), 'registrationDeadline': _local(t.registration_deadline),
                'meetingPoint': t.meeting_point, 'difficulty': t.difficulty, 'lengthKm': float(t.length_km),
                'elevationGainM': t.elevation_gain_m, 'durationH': float(t.duration_h),
                'maxParticipants': t.max_participants, 'price': float(t.price), 'membersOnly': t.members_only,
                'requiredEquipment': t.required_equipment, 'route': t.route or [],
            },
            'registrations': [{'id': r.pk, 'name': r.user.get_full_name(),
                               'status': {'code': r.status, 'label': r.get_status_display()},
                               'attendance': r.get_attendance_display() if r.attendance else None} for r in regs],
            'guideApplications': [{'id': a.pk, 'name': a.user.get_full_name(),
                                   'status': {'code': a.status, 'label': a.get_status_display()}} for a in apps],
            'assignable': [{'id': g.pk, 'name': g.user.get_full_name()} for g in assignable],
        })

    def put(self, request, club_pk, pk):
        tour = svc.club_tour(self.club, pk)
        try:
            svc.ensure_editable(tour)
        except svc.ClubError as e:
            return _err(e)
        form = _tour_form(request, instance=tour)
        if not form.is_valid():
            return _form_error_response(form)
        try:
            svc.edit_tour(request._request, self.club, pk, form)
        except svc.ClubError as e:
            return _err(e)
        return Response({'id': tour.pk, 'detail': 'Tura je sačuvana.'})


class TourTransitionView(ClubAdminView):
    def post(self, request, club_pk, pk):
        action = _body(request).get('action')
        if not isinstance(action, str):
            raise Http404
        try:
            return Response({'detail': svc.transition(request._request, self.club, pk, action)})
        except svc.ClubError as e:
            return _err(e)


class GuideAssignView(ClubAdminView):
    def post(self, request, club_pk, pk):
        gid = _body(request).get('guideId')
        if not isinstance(gid, int) or isinstance(gid, bool):
            raise Http404
        try:
            return Response({'detail': svc.assign_guide(request._request, self.club, pk, gid)})
        except svc.ClubError as e:
            return _err(e)


class GuideDecideView(ClubAdminView):
    def post(self, request, club_pk, pk, app_pk):
        decision = _body(request).get('decision')
        try:
            svc.decide_guide(request._request, self.club, pk, app_pk, decision if isinstance(decision, str) else '')
        except svc.ClubError as e:
            return _err(e)
        return Response({'detail': 'Odluka je sačuvana.'})


class MembersView(ClubAdminView):
    """F26, F28 - zahtjevi i aktivni članovi (ime i datumi; bez kontakt podataka, kao HTML panel)."""

    def get(self, request, club_pk):
        pending, active = svc.members(self.club)

        def row(m):
            return {'id': m.pk, 'name': m.user.get_full_name(),
                    'createdAt': m.created_at.isoformat(),
                    'validUntil': m.valid_until.isoformat() if m.valid_until else None}
        return Response({'pending': [row(m) for m in pending], 'active': [row(m) for m in active]})


class MembershipDecideView(ClubAdminView):
    def post(self, request, club_pk, pk):
        decision = _body(request).get('decision')
        svc.decide_membership(request._request, self.club, pk, decision if isinstance(decision, str) else '')
        return Response({'detail': 'Odluka je sačuvana.'})

