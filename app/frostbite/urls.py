"""Django služi samo JSON API (/api/). Interfejs je React aplikacija (frontend/), koju servira Nginx."""
from django.urls import include, path

urlpatterns = [
    path('api/auth/', include('accounts.api_urls')),
    path('api/tours/', include('tours.api_urls')),
    path('api/clubs/', include('clubs.api_urls')),
    path('api/selection/', include('tours.api_selection_urls')),
    path('api/badges/', include('badges.api_urls')),
    path('api/me/', include('accounts.api_me_urls')),
    path('api/guide/', include('panel.api_guide_urls')),
    path('api/manage/', include('panel.api_club_urls')),
    path('api/system/', include('panel.api_system_urls')),
]

handler400 = 'frostbite.views.bad_request'
handler403 = 'frostbite.views.permission_denied'
handler404 = 'frostbite.views.not_found'
handler500 = 'frostbite.views.server_error'
