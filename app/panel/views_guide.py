"""Funkcionalnosti vodiča (F15-F20) - HTML stranice. Pravila su u panel.guide_service."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.permissions import guide_required

from . import guide_service as svc
from .forms import ReportForm


@guide_required
@require_GET
def dashboard(request):
    """F15 - ture vlastitih društava bez vodiča + ture koje korisnik vodi."""
    return render(request, 'panel/guide_dashboard.html',
                  {'open_tours': svc.open_tours(request.user), 'mine': svc.my_tours(request.user)})


@guide_required
@require_POST
def apply(request, pk):
    """F16 - prijava za vođenje ture vlastitog društva."""
    try:
        svc.apply(request, pk)
        messages.success(request, 'Prijava za vođenje je poslana adminu društva.')
    except svc.GuideError as e:
        messages.error(request, str(e))
    return redirect('panel:guide')


@guide_required
@require_GET
def tour_participants(request, pk):
    """F17 - učesnici ture sa ličnim podacima (samo odobreni vodič, ograničenje 1)."""
    tour, regs, report = svc.participants(request, pk)
    can_attend = svc.attendance_open(tour)
    from tours.views import start_point
    return render(request, 'panel/guide_tour.html', {
        'tour': tour, 'regs': regs, 'can_attend': can_attend, 'report': report, 'start': start_point(tour),
        'report_form': ReportForm() if can_attend and not report else None,
    })


@guide_required
@require_POST
def close_registrations(request, pk):
    """F18 - zatvaranje prijava (OBJAVLJENA -> PRIJAVE ZATVORENE)."""
    try:
        svc.close_registrations(request, pk)
        messages.success(request, 'Prijave su zatvorene.')
    except svc.GuideError as e:
        messages.error(request, str(e))
    return redirect('panel:guide_tour', pk=pk)


@guide_required
@require_POST
def attendance(request, pk):
    """F19 - evidencija prisustva (od 12 sati prije polaska)."""
    present = {int(raw) for raw in request.POST.getlist('present') if raw.isdigit()}
    try:
        svc.save_attendance(request, pk, present)
        messages.success(request, 'Prisustvo je sačuvano.')
    except svc.GuideError as e:
        messages.error(request, str(e))
    return redirect('panel:guide_tour', pk=pk)


@guide_required
@require_http_methods(['POST'])
def report(request, pk):
    """F20 - izvještaj sa ture; tura prelazi u status ODRŽANA."""
    try:
        svc.save_report(request, pk, request.POST)
        messages.success(request, 'Izvještaj je sačuvan, a tura je označena kao održana.')
    except svc.GuideError as e:
        messages.error(request, str(e))
    return redirect('panel:guide_tour', pk=pk)
