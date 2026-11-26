from .models import Club


def approved_clubs():
    return Club.objects.filter(status=Club.Status.APPROVED)
