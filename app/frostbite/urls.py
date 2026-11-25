from django.templatetags.static import static
from django.urls import include, path
from django.views.generic.base import RedirectView

from tours import views as tour_views

urlpatterns = [
    path('', tour_views.home, name='home'),
    path('favicon.ico', RedirectView.as_view(url=static('favicon.ico'), permanent=True)),
    path('', include('tours.urls')),
    path('', include('clubs.urls')),
    path('nalog/', include('accounts.urls')),
    path('api/auth/', include('accounts.api_urls')),
    path('', include('panel.urls')),
]
