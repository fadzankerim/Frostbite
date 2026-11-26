"""API bedževa: javni katalog (/api/badges/) i vlastiti bedževi (/api/me/badges/).

Bedževi otkrivaju aktivnost korisnika, pa ih vidi samo vlasnik naloga. Katalog je samo za čitanje.
"""
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from frostbite.api import ApiView

from . import services
from .models import Badge, UserBadge


def badge_payload(b):
    return {'code': b.code, 'name': b.name, 'description': b.description,
            'role': b.role, 'tier': b.tier, 'icon': b.icon}


class BadgeCatalogView(ApiView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'results': [badge_payload(b) for b in Badge.objects.all()],
            'awardedTotal': UserBadge.objects.count(),
        })


class MyBadgesView(ApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        results = []
        for b, ub, progress, goal in services.my_badges(request.user):
            results.append({
                **badge_payload(b),
                'earned': ub is not None,
                'awardedAt': ub.awarded_at if ub else None,
                'seen': ub.seen if ub else True,
                'progress': progress,
                'goal': goal,
            })
        return Response({'results': results})


class MyBadgesSeenView(ApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({'updated': services.mark_seen(request.user)})
