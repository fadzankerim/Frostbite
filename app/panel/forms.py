import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from clubs.models import Club
from tours.models import Tour, TourRegistration, TourReport, validate_route

DT_FORMAT = '%Y-%m-%dT%H:%M'


class DateTimeLocal(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, **kw):
        super().__init__(format=DT_FORMAT, **kw)


class TourForm(forms.ModelForm):
    """F23 - kreiranje i uređivanje ture. Društvo, status i autor NISU dio forme (postavlja ih server)."""
    route = forms.CharField(required=False, widget=forms.HiddenInput, max_length=40000)

    class Meta:
        model = Tour
        fields = ['name', 'region', 'description', 'start_at', 'registration_deadline', 'meeting_point',
                  'difficulty', 'length_km', 'elevation_gain_m', 'duration_h', 'max_participants', 'price',
                  'members_only', 'required_equipment']
        widgets = {
            'start_at': DateTimeLocal(), 'registration_deadline': DateTimeLocal(),
            'description': forms.Textarea(attrs={'rows': 4, 'maxlength': 4000}),
            'required_equipment': forms.Textarea(attrs={'rows': 2, 'maxlength': 1000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('start_at', 'registration_deadline'):
            self.fields[f].input_formats = [DT_FORMAT]
        if self.instance.pk and not self.is_bound:
            self.initial['route'] = json.dumps(self.instance.route or [])

    def clean_route(self):
        raw = (self.cleaned_data.get('route') or '').strip()
        if not raw:
            return []
        try:
            value = json.loads(raw)
        except (ValueError, TypeError):
            raise ValidationError('Ruta nije u ispravnom formatu.')
        # JSON brojevi -> float; validate_route odbija sve ostalo
        validate_route(value)
        return [[round(float(lat), 6), round(float(lng), 6)] for lat, lng in value]

    def clean(self):
        data = super().clean()
        start, deadline = data.get('start_at'), data.get('registration_deadline')
        now = timezone.now()
        if start and deadline and deadline > start:
            self.add_error('registration_deadline', 'Rok prijave mora biti prije polaska.')
        if start and (not self.instance.pk or start != self.instance.start_at) and start <= now:
            self.add_error('start_at', 'Polazak mora biti u budućnosti.')
        maxp = data.get('max_participants')
        if self.instance.pk and maxp:
            taken = self.instance.registrations.filter(status=TourRegistration.Status.REGISTERED).count()
            if maxp < taken:
                self.add_error('max_participants', f'Na turu je već prijavljeno {taken} učesnika.')
        return data

    def save(self, commit=True):
        self.instance.route = self.cleaned_data.get('route') or []
        return super().save(commit)


class ClubProfileForm(forms.ModelForm):
    """F21 - profil društva. Naziv i status mijenja samo sistemski admin (nije dio forme)."""

    class Meta:
        model = Club
        fields = ['city', 'description', 'email', 'phone']
        widgets = {'description': forms.Textarea(attrs={'rows': 5, 'maxlength': 2000})}


class AddGuideForm(forms.Form):
    """F22 - dodavanje vodiča po emailu postojećeg korisnika."""
    email = forms.EmailField(label='Email planinara', max_length=254)
    license_number = forms.CharField(label='Broj licence', max_length=40, required=False)

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class ReportForm(forms.ModelForm):
    """F20 - izvještaj sa ture."""

    class Meta:
        model = TourReport
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows': 6, 'maxlength': 4000})}


class UserSearchForm(forms.Form):
    q = forms.CharField(label='Pretraga', max_length=100, required=False,
                        widget=forms.TextInput(attrs={'placeholder': 'Ime, prezime ili email'}))


class AuditFilterForm(forms.Form):
    action = forms.CharField(label='Akcija', max_length=50, required=False,
                             widget=forms.TextInput(attrs={'placeholder': 'npr. LOGIN_NEUSPJEH'}))
