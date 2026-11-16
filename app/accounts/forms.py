from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from .models import User

GENERIC_LOGIN_ERROR = 'Pogrešan email ili lozinka, ili je nalog privremeno zaključan.'


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', max_length=254,
                                widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email'}))
    error_messages = {
        'invalid_login': GENERIC_LOGIN_ERROR,
        'inactive': GENERIC_LOGIN_ERROR,     # ista poruka: ne otkriva da je nalog blokiran
    }


class RegistrationForm(forms.Form):
    """Registracija planinara (F05).

    Namjerno NIJE ModelForm: provjera jedinstvenosti emaila bi otkrila da nalog postoji
    (politika 4.4). Duplikat se obrađuje u view-u isto kao uspješna registracija.
    """
    email = forms.EmailField(label='Email', max_length=254, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    first_name = forms.CharField(label='Ime', max_length=60)
    last_name = forms.CharField(label='Prezime', max_length=60)
    phone = forms.CharField(label='Telefon', max_length=30, required=False)
    password1 = forms.CharField(label='Lozinka', strip=False,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
                                help_text='Najmanje 10 znakova; ne smije biti česta lozinka niti slična imenu ili emailu.')
    password2 = forms.CharField(label='Ponovite lozinku', strip=False,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Lozinke se ne podudaraju.')
        if p1 and not self.has_error('password2'):
            candidate = User(email=data.get('email', ''), first_name=data.get('first_name', ''),
                             last_name=data.get('last_name', ''))
            try:
                password_validation.validate_password(p1, candidate)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return data


class ProfileForm(forms.ModelForm):
    """Uređivanje vlastitog profila (F07). Email, uloge i status nisu dio forme."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'emergency_contact_name', 'emergency_contact_phone', 'health_notes']
        widgets = {'health_notes': forms.Textarea(attrs={'rows': 4, 'maxlength': 1000})}
        help_texts = {
            'health_notes': 'Vidljivo samo vama i vodiču ture na koju ste prijavljeni (npr. alergije, dijabetes).',
            'emergency_contact_name': 'Osoba koju vodič kontaktira u slučaju nezgode.',
        }


class BosnianPasswordChangeForm(PasswordChangeForm):
    error_messages = {
        **PasswordChangeForm.error_messages,
        'password_incorrect': 'Trenutna lozinka nije ispravna.',
        'password_mismatch': 'Nove lozinke se ne podudaraju.',
    }
