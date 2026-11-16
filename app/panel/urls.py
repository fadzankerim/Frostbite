from django.urls import path

from . import views_club as club
from . import views_guide as guide
from . import views_system as system

app_name = 'panel'

urlpatterns = [
    # vodič (F15-F20)
    path('vodic/', guide.dashboard, name='guide'),
    path('vodic/ture/<int:pk>/prijava/', guide.apply, name='guide_apply'),
    path('vodic/ture/<int:pk>/', guide.tour_participants, name='guide_tour'),
    path('vodic/ture/<int:pk>/zatvori/', guide.close_registrations, name='guide_close'),
    path('vodic/ture/<int:pk>/prisustvo/', guide.attendance, name='guide_attendance'),
    path('vodic/ture/<int:pk>/izvjestaj/', guide.report, name='guide_report'),

    # admin društva (F18, F21-F28)
    path('upravljanje/', club.choose_club, name='club_choose'),
    path('upravljanje/<int:club_pk>/', club.club_dashboard, name='club'),
    path('upravljanje/<int:club_pk>/ture/', club.club_tours, name='club_tours'),
    path('upravljanje/<int:club_pk>/profil/', club.club_profile, name='club_profile'),
    path('upravljanje/<int:club_pk>/vodici/', club.guides, name='guides'),
    path('upravljanje/<int:club_pk>/vodici/<int:pk>/ukloni/', club.guide_remove, name='guide_remove'),
    path('upravljanje/<int:club_pk>/ture/nova/', club.tour_create, name='tour_create'),
    path('upravljanje/<int:club_pk>/ture/<int:pk>/', club.club_tour_detail, name='club_tour'),
    path('upravljanje/<int:club_pk>/ture/<int:pk>/uredi/', club.tour_edit, name='tour_edit'),
    path('upravljanje/<int:club_pk>/ture/<int:pk>/dodijeli-vodica/', club.guide_assign, name='guide_assign'),
    path('upravljanje/<int:club_pk>/ture/<int:pk>/<str:action>/', club.tour_transition, name='tour_transition'),
    path('upravljanje/<int:club_pk>/ture/<int:pk>/vodic/<int:app_pk>/<str:decision>/', club.guide_decide, name='guide_decide'),
    path('upravljanje/<int:club_pk>/clanovi/', club.members, name='members'),
    path('upravljanje/<int:club_pk>/clanovi/<int:pk>/<str:decision>/', club.membership_decide, name='membership_decide'),

    # sistemski admin (F29-F31)
    path('sistem/', system.dashboard, name='sys_dashboard'),
    path('sistem/drustva/', system.clubs, name='sys_clubs'),
    path('sistem/drustva/<int:pk>/<str:action>/', system.club_decide, name='sys_club_decide'),
    path('sistem/korisnici/', system.users, name='sys_users'),
    path('sistem/korisnici/<int:pk>/blokada/', system.user_toggle, name='sys_user_toggle'),
    path('sistem/evidencija/', system.audit_log, name='sys_audit'),
]
