"""Funkcionalnosti admina društva (F18, F21-F28) - HTML stranice. Pravila su u panel.club_service.

Svaki view dobija `club` iz club_admin_required (samo društva kojima korisnik upravlja),
i svaki objekat se traži UNUTAR tog društva - tuđe ture, vodiči i članstva daju 404.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.permissions import admin_clubs, club_admin_required
from clubs.models import ClubGuide, ClubMembership

from . import club_service as svc
from .forms import AddGuideForm, ClubProfileForm, TourForm

EDITABLE = svc.EDITABLE
TRANSITIONS = svc.TRANSITIONS
club_tour = svc.club_tour


@login_required
@require_GET
def choose_club(request):
    """Ako korisnik upravlja sa više društava, bira jedno."""
    clubs = list(admin_clubs(request.user))
    if len(clubs) == 1:
        return redirect('panel:club', club_pk=clubs[0].pk)
    if not clubs:
        return redirect('home')
    return render(request, 'panel/club_choose.html', {'clubs': clubs})


@club_admin_required
@require_GET
def club_dashboard(request, club):
    """Početna stranica admina društva: analitika (ture po fazama, vodiči, članovi, učesnici, prihod)."""
    from .charts import column_chart

    d = svc.dashboard(club)
    gmax = max([c for _, c in d['guide_rows']] + [1])
    return render(request, 'panel/club_dashboard.html', {
        'club': club, 'tab': 'overview',
        'phases': d['phases'], 'money': d['money'], 'fill': d['fill'],
        'guides_count': len(d['guide_rows']),
        'unguided': d['unguided'],
        'guide_rows': [(n, c, gmax) for n, c in d['guide_rows']],
        'members_count': d['members_count'],
        'pending_members': d['pending_members'],
        'pending_guides': d['pending_guides'],
        'upcoming': d['active'][:6],
        'people_chart': column_chart([(label, p) for label, p, _ in d['months']]),
        'money_chart': column_chart([(label, m) for label, _, m in d['months']], unit=' KM'),
    })


@club_admin_required
@require_GET
def club_tours(request, club):
    """Sve ture društva (F23, F24, F27)."""
    upcoming, past = svc.tours_overview(club)
    return render(request, 'panel/club_tours.html', {
        'club': club, 'tab': 'tours', 'upcoming': upcoming, 'past': past,
        'pending_members': ClubMembership.objects.filter(club=club, status=ClubMembership.Status.REQUESTED).count(),
        'guides_count': ClubGuide.objects.filter(club=club, is_active=True).count(),
    })


# --- F21 profil ---------------------------------------------------------------
@club_admin_required
@require_http_methods(['GET', 'POST'])
def club_profile(request, club):
    form = ClubProfileForm(request.POST or None, instance=club)
    if request.method == 'POST' and form.is_valid():
        svc.save_profile(request, club, form)
        messages.success(request, 'Profil društva je sačuvan.')
        return redirect('panel:club', club_pk=club.pk)
    return render(request, 'panel/club_profile.html', {'club': club, 'form': form})


# --- F22 vodiči ---------------------------------------------------------------
@club_admin_required
@require_http_methods(['GET', 'POST'])
def guides(request, club):
    form = AddGuideForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        svc.add_guide(request, club, form.cleaned_data['email'], form.cleaned_data['license_number'])
        messages.info(request, svc.ADD_GUIDE_MSG)        # ista poruka - bez otkrivanja naloga
        return redirect('panel:guides', club_pk=club.pk)
    return render(request, 'panel/club_guides.html', {'club': club, 'form': form, 'items': svc.club_guides(club)})


@club_admin_required
@require_POST
def guide_remove(request, club, pk):
    g = svc.remove_guide(request, club, pk)
    messages.success(request, f'{g.user.get_full_name()} više nije vodič društva.')
    return redirect('panel:guides', club_pk=club.pk)


# --- F23, F24 ture ------------------------------------------------------------
@club_admin_required
@require_http_methods(['GET', 'POST'])
def tour_create(request, club):
    form = TourForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        tour = svc.create_tour(request, club, form)
        messages.success(request, 'Tura je sačuvana kao nacrt. Objavite je kada bude spremna.')
        return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
    return render(request, 'panel/tour_form.html', {'club': club, 'form': form, 'tour': None})


@club_admin_required
@require_http_methods(['GET', 'POST'])
def tour_edit(request, club, pk):
    tour = svc.club_tour(club, pk)
    try:
        svc.ensure_editable(tour)
    except svc.ClubError as e:
        messages.error(request, str(e))
        return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
    form = TourForm(request.POST or None, instance=tour)
    if request.method == 'POST' and form.is_valid():
        try:
            svc.edit_tour(request, club, pk, form)
            messages.success(request, 'Tura je sačuvana.')
        except svc.ClubError as e:
            messages.error(request, str(e))
        return redirect('panel:club_tour', club_pk=club.pk, pk=tour.pk)
    return render(request, 'panel/tour_form.html', {'club': club, 'form': form, 'tour': tour})


@club_admin_required
@require_POST
def tour_transition(request, club, pk, action):
    """F24 (objava, otkazivanje) i F18 (zatvaranje prijava)."""
    try:
        messages.success(request, svc.transition(request, club, pk, action))
    except svc.ClubError as e:
        messages.error(request, str(e))
    return redirect('panel:club_tour', club_pk=club.pk, pk=pk)


@club_admin_required
@require_GET
def club_tour_detail(request, club, pk):
    """F25 (prijave vodiča) i F27 (prijave na turu: ime, prezime, status - BEZ ličnih podataka)."""
    tour, regs, apps, assignable = svc.tour_detail(club, pk)
    return render(request, 'panel/club_tour.html', {
        'club': club, 'tour': tour, 'regs': regs, 'apps': apps, 'editable': tour.status in EDITABLE,
        'assignable': assignable,
    })


# --- F25 odobravanje i dodjela vodiča ----------------------------------------
@club_admin_required
@require_POST
def guide_assign(request, club, pk):
    """Admin direktno dodjeljuje aktivnog vodiča SVOG društva turi (bez prijave vodiča)."""
    raw = request.POST.get('guide', '')
    try:
        messages.success(request, svc.assign_guide(request, club, pk, int(raw) if raw.isdigit() else -1))
    except svc.ClubError as e:
        messages.error(request, str(e))
    return redirect('panel:club_tour', club_pk=club.pk, pk=pk)


@club_admin_required
@require_POST
def guide_decide(request, club, pk, app_pk, decision):
    try:
        svc.decide_guide(request, club, pk, app_pk, decision)
        messages.success(request, 'Odluka je sačuvana.')
    except svc.ClubError as e:
        messages.error(request, str(e))
    return redirect('panel:club_tour', club_pk=club.pk, pk=pk)


# --- F26, F28 članstva --------------------------------------------------------
@club_admin_required
@require_GET
def members(request, club):
    pending, active = svc.members(club)
    return render(request, 'panel/club_members.html', {'club': club, 'pending': pending, 'active': active})


@club_admin_required
@require_POST
def membership_decide(request, club, pk, decision):
    svc.decide_membership(request, club, pk, decision)
    messages.success(request, 'Odluka je sačuvana.')
    return redirect('panel:members', club_pk=club.pk)
