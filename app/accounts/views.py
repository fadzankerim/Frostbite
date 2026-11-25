from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from audit.log import audit

from .forms import BosnianPasswordChangeForm, LoginForm, ProfileForm, RegistrationForm
from .services import register_hiker

REGISTER_DONE_MSG = 'Registracija je završena. Prijavite se svojim emailom i lozinkom.'


@require_http_methods(['GET', 'POST'])
def register(request):
    """F05 - registracija planinara. Dostupno samo neprijavljenim korisnicima."""
    if request.user.is_authenticated:
        return redirect('home')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        register_hiker(request, form.cleaned_data)
        messages.success(request, REGISTER_DONE_MSG)
        return redirect('accounts:login')
    return render(request, 'accounts/register.html', {'form': form})


def landing_url(user):
    """Početna stranica prema ulozi: sistemski admin i admin društva -> analitika,
    vodič -> ture za koje se može prijaviti, planinar -> početna."""
    from django.urls import reverse

    from .permissions import is_club_admin, is_guide
    if user.is_system_admin:
        return reverse('panel:sys_dashboard')
    if is_club_admin(user):
        return reverse('panel:club_choose')
    if is_guide(user):
        return reverse('panel:guide')
    return reverse('home')


class LoginView(auth_views.LoginView):
    """F06 - prijava. Django LoginView: nova sesija pri prijavi, siguran 'next' parametar
    (provjeren protiv otvorenog preusmjeravanja); bez njega - početna stranica uloge."""
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or landing_url(self.request.user)


class LogoutView(auth_views.LogoutView):
    """F06 - odjava (samo POST, sesija se briše)."""


@login_required
@require_http_methods(['GET', 'POST'])
def profile(request):
    """F07 - pregled i uređivanje vlastitog profila."""
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        audit(request, 'PROFIL_IZMJENA', 'user', request.user.pk)
        messages.success(request, 'Profil je sačuvan.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'form': form})


class PasswordChangeView(auth_views.PasswordChangeView):
    """F08 - promjena lozinke. Ostale sesije korisnika postaju nevažeće (Django mijenja hash sesije)."""
    template_name = 'accounts/password_change.html'
    form_class = BosnianPasswordChangeForm
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        audit(self.request, 'LOZINKA_PROMJENA', 'user', self.request.user.pk)
        messages.success(self.request, 'Lozinka je promijenjena.')
        return response
