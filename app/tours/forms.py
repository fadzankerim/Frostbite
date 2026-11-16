from django import forms
from django.db.models import Q

from clubs.models import Club

from .models import Tour


class TourSearchForm(forms.Form):
    """F02 - pretraga i filtriranje javno vidljivih tura."""
    q = forms.CharField(label='Pretraga', max_length=80, required=False,
                        widget=forms.TextInput(attrs={'placeholder': 'Naziv ture ili regija'}))
    difficulty = forms.ChoiceField(label='Težina', required=False,
                                   choices=[('', 'Sve težine')] + list(Tour.Difficulty.choices))
    club = forms.ModelChoiceField(label='Društvo', required=False, empty_label='Sva društva',
                                  queryset=Club.objects.filter(status=Club.Status.APPROVED))
    date_from = forms.DateField(label='Od', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(label='Do', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def filter(self, qs):
        if not self.is_valid():
            return qs
        d = self.cleaned_data
        if d['q']:
            qs = qs.filter(Q(name__icontains=d['q']) | Q(region__icontains=d['q']))
        if d['difficulty']:
            qs = qs.filter(difficulty=d['difficulty'])
        if d['club']:
            qs = qs.filter(club=d['club'])
        if d['date_from']:
            qs = qs.filter(start_at__date__gte=d['date_from'])
        if d['date_to']:
            qs = qs.filter(start_at__date__lte=d['date_to'])
        return qs
