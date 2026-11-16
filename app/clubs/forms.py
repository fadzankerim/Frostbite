from django import forms

from .models import Club


class ClubRequestForm(forms.ModelForm):
    """F09 - zahtjev za registraciju društva. Status, admin i datum postavlja server."""

    class Meta:
        model = Club
        fields = ['name', 'city', 'description', 'email', 'phone']
        widgets = {'description': forms.Textarea(attrs={'rows': 4, 'maxlength': 2000})}

    def validate_unique(self):
        # Jedinstvenost naziva provjerava view (generička poruka).
        pass
