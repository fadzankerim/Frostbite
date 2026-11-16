from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.permissions import hiker_required
from audit.log import audit
from tours.views import public_tours

from .forms import ClubRequestForm
from .models import Club, ClubAdmin, ClubMembership

MAX_PENDING_CLUB_REQUESTS = 1


def approved_clubs():
    return Club.objects.filter(status=Club.Status.APPROVED)


@require_GET
def club_list(request):
    """F04 - lista odobrenih društava (javno)."""
    return render(request, 'clubs/list.html', {'clubs': approved_clubs()})


@require_GET
def club_detail(request, pk):
    """F04 - javni profil društva i njegove javno vidljive ture."""
    club = get_object_or_404(approved_clubs(), pk=pk)
    membership = None
    if request.user.is_authenticated:
        membership = (ClubMembership.objects.filter(club=club, user=request.user)
                      .order_by('-created_at').first())
    return render(request, 'clubs/detail.html', {
        'club': club,
        'tours': public_tours().filter(club=club).order_by('start_at'),
        'membership': membership,
    })


@hiker_required
@require_POST
def membership_request(request, pk):
    """F13 - zahtjev za učlanjenje u odobreno društvo."""
    club = get_object_or_404(approved_clubs(), pk=pk)
    try:
        with transaction.atomic():
            m = ClubMembership.objects.create(club=club, user=request.user)
        audit(request, 'CLANSTVO_ZAHTJEV', 'club_membership', m.pk, details=f'drustvo={club.pk}')
        messages.success(request, 'Zahtjev za učlanjenje je poslan. Društvo će ga razmotriti.')
    except IntegrityError:
        messages.error(request, 'Već imate aktivan zahtjev ili članstvo u ovom društvu.')
    return redirect('clubs:detail', pk=club.pk)


@hiker_required
@require_GET
def my_memberships(request):
    """F14 - vlastita članstva i zahtjevi."""
    items = ClubMembership.objects.filter(user=request.user).select_related('club').order_by('-created_at')
    today = timezone.localdate()
    for m in items:
        m.expired = m.status == ClubMembership.Status.APPROVED and m.valid_until and m.valid_until < today
    return render(request, 'clubs/my_memberships.html', {'items': items})


@hiker_required
@require_http_methods(['GET', 'POST'])
def club_register(request):
    """F09 - zahtjev za registraciju društva. Podnosilac postaje admin društva tek kad
    sistemski admin odobri društvo (admin_clubs() uzima samo odobrena društva)."""
    pending = Club.objects.filter(created_by=request.user, status=Club.Status.PENDING).count()
    form = ClubRequestForm(request.POST or None)
    if pending >= MAX_PENDING_CLUB_REQUESTS:
        messages.info(request, 'Već imate zahtjev za registraciju društva koji čeka odobrenje.')
        return redirect('clubs:list')
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                club = form.save(commit=False)
                club.status = Club.Status.PENDING
                club.created_by = request.user
                club.save()
                ClubAdmin.objects.create(club=club, user=request.user)
            audit(request, 'DRUSTVO_ZAHTJEV', 'club', club.pk)
            messages.success(request, 'Zahtjev je poslan. Društvo postaje vidljivo nakon odobrenja.')
            return redirect('clubs:list')
        except IntegrityError:
            form.add_error('name', 'Ovaj naziv nije dostupan.')
    return render(request, 'clubs/register.html', {'form': form})
