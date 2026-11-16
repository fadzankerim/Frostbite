from django.shortcuts import render


def csrf_failure(request, reason=''):
    # Razlog se ne prikazuje korisniku (bez otkrivanja internih detalja).
    return render(request, '403_csrf.html', status=403)
