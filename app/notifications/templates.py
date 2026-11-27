"""Šabloni emailova: naslov i kratki sažetak (za dnevni i sedmični pregled) po šablonu. Tijelo je u
templates/email/<šablon>.txt. HTML verzija se pravi iz teksta (sav tekst escapiran), pa korisnički
sadržaj (naziv ture, društva) nikad ne postaje HTML."""
import re

from django.template.loader import render_to_string
from django.utils.html import escape

SUBJECTS = {
    # planinar
    'prijava_potvrda': ('Prijava na turu: {tour}', 'Prijava na turu „{tour}“ ({start})'),
    'lista_cekanja_mjesto': ('Dobili ste mjesto na turi: {tour}', 'Dobili ste mjesto na turi „{tour}“'),
    'tura_otkazana': ('Tura je otkazana: {tour}', 'Otkazana tura „{tour}“ ({start})'),
    'tura_izmijenjena': ('Izmjena ture: {tour}', 'Izmijenjen termin ili mjesto polaska ture „{tour}“'),
    'podsjetnik': ('Sutra: {tour}', 'Podsjetnik: „{tour}“ sutra ({start})'),
    'nova_tura': ('Nova tura društva {club}: {tour}', 'Nova tura „{tour}“ ({start}), {club}'),
    'clanstvo_odluka': ('Odluka o članstvu: {club}', 'Odluka o članstvu u društvu {club}'),
    'drustvo_odluka': ('Odluka o registraciji društva: {club}', 'Odluka o registraciji društva {club}'),
    # vodič
    'tura_bez_vodica': ('Tura bez vodiča: {tour}', 'Tura bez vodiča „{tour}“ ({start})'),
    'vodjenje_odluka': ('Odluka o vođenju ture: {tour}', 'Odluka o vođenju ture „{tour}“'),
    'vodic_dodijeljen': ('Dodijeljeni ste kao vodič: {tour}', 'Dodijeljeni ste kao vodič ture „{tour}“'),
    'ucesnici_promjena': ('{action} na turi {tour}', '{name}: {action_lower} („{tour}“, prijavljeno {registered}/{max})'),
    # admin društva
    'clanstvo_zahtjev': ('Novi zahtjev za članstvo: {club}', 'Zahtjev za članstvo: {name}'),
    'vodic_prijava': ('Prijava za vođenje ture: {tour}', '{name} se prijavio/la za vođenje ture „{tour}“'),
    'tura_popunjena': ('Tura je popunjena: {tour}', 'Popunjena tura „{tour}“ ({start})'),
    'tura_bez_vodica_upozorenje': ('Tura nema vodiča: {tour}', 'Tura „{tour}“ ({start}) još nema vodiča'),
    # sistemski admin
    'drustvo_zahtjev': ('Novi zahtjev za registraciju društva: {club}', 'Zahtjev za registraciju društva {club} ({city})'),
    # sigurnost
    'lozinka_promijenjena': ('Lozinka je promijenjena', 'Lozinka je promijenjena'),
    'nalog_zakljucan': ('Nalog je privremeno zaključan', 'Nalog je privremeno zaključan'),
    'nalog_blokiran': ('Nalog je blokiran', 'Nalog je blokiran'),
    'registracija_postojeci': ('Pokušaj registracije s vašim emailom', 'Pokušaj registracije s vašim emailom'),
}

_CONTROL = re.compile(r'[\x00-\x1f\x7f]')
_URL = re.compile(r'(https://[^\s<>"]+)')


def clean(value, limit=200):
    """Jedan red teksta: bez kontrolnih znakova (zaglavlja emaila), ograničene dužine."""
    return _CONTROL.sub(' ', str(value)).strip()[:limit]


def subject(template, ctx):
    return clean(SUBJECTS[template][0].format(**ctx), 150)


def summary(template, ctx):
    return clean(SUBJECTS[template][1].format(**ctx), 300)


def render_text(name, ctx):
    return render_to_string(f'email/{name}.txt', ctx).strip() + '\n'


def text_to_html(text):
    """Escapira cijeli tekst, pa pravi pasuse i klikabilne linkove samo za naše https:// linkove."""
    parts = []
    for para in text.strip().split('\n\n'):
        html = escape(para).replace('\n', '<br>')
        html = _URL.sub(r'<a href="\1">\1</a>', html)
        parts.append(f'<p>{html}</p>')
    return ('<!doctype html><html lang="bs"><head><meta charset="utf-8"></head>'
            '<body style="font-family:sans-serif;line-height:1.5;max-width:560px">' + ''.join(parts) + '</body></html>')
