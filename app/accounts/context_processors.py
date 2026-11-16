from .permissions import is_club_admin, is_guide


def roles(request):
    """Uloge za prikaz menija. Samo za prikaz - svaki view provjerava prava ponovo na serveru."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'role_admin': False, 'role_guide': False, 'role_sysadmin': False}
    return {
        'role_sysadmin': user.is_system_admin,
        'role_admin': is_club_admin(user),
        'role_guide': is_guide(user),
    }
