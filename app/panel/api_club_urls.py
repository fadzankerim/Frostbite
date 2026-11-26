from django.urls import path

from . import api_club as api

app_name = 'api_manage'

urlpatterns = [
    path('', api.ManagedClubsView.as_view(), name='clubs'),
    path('<int:club_pk>/', api.DashboardView.as_view(), name='dashboard'),
    path('<int:club_pk>/profile/', api.ProfileView.as_view(), name='profile'),
    path('<int:club_pk>/guides/', api.GuidesView.as_view(), name='guides'),
    path('<int:club_pk>/guides/<int:pk>/remove/', api.GuideRemoveView.as_view(), name='guide_remove'),
    path('<int:club_pk>/tours/', api.ToursView.as_view(), name='tours'),
    path('<int:club_pk>/tours/<int:pk>/', api.TourView.as_view(), name='tour'),
    path('<int:club_pk>/tours/<int:pk>/transition/', api.TourTransitionView.as_view(), name='transition'),
    path('<int:club_pk>/tours/<int:pk>/guides/assign/', api.GuideAssignView.as_view(), name='assign'),
    path('<int:club_pk>/tours/<int:pk>/guides/<int:app_pk>/decide/', api.GuideDecideView.as_view(), name='decide'),
    path('<int:club_pk>/members/', api.MembersView.as_view(), name='members'),
    path('<int:club_pk>/members/<int:pk>/decide/', api.MembershipDecideView.as_view(), name='member_decide'),
]
