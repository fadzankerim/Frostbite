"""Pomoćna funkcija za upis u evidenciju aktivnosti."""
from .models import AuditLog


def client_ip(request):
    # Nginx postavlja X-Real-IP; direktno REMOTE_ADDR je uvijek Nginx (unix socket).
    # Napomena: zbog NAT-a na VPN serveru svi recenzenti imaju istu IP adresu.
    if request is None:
        return None
    ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')
    return ip or None


def audit(request, action, entity='', entity_id='', details='', user=None):
    if user is None and request is not None and request.user.is_authenticated:
        user = request.user
    return AuditLog.objects.create(
        user=user, action=action[:50], entity=entity[:50], entity_id=str(entity_id)[:50],
        details=details[:500], ip=client_ip(request),
    )
