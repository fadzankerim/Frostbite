"""GPX izvoz rute javne ture (/api/tours/<id>/gpx/) - za Google My Maps, Wikiloc, Komoot, GPS uređaje.
GPX generiše server iz provjerenih koordinata; tekst (naziv, društvo, mjesto) je XML-escapiran."""
from xml.sax.saxutils import escape

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .queries import public_tours


@require_GET
def tour_gpx(request, pk):
    tour = get_object_or_404(public_tours(), pk=pk)
    if not (isinstance(tour.route, list) and len(tour.route) >= 2):
        raise Http404
    pts = ''.join(f'<trkpt lat="{float(lat):.6f}" lon="{float(lng):.6f}"/>' for lat, lng in tour.route)
    lat0, lng0 = tour.route[0]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<gpx version="1.1" creator="Frostbite" xmlns="http://www.topografix.com/GPX/1/1">'
           f'<metadata><name>{escape(tour.name)}</name><desc>{escape(tour.club.name)}</desc></metadata>'
           f'<wpt lat="{float(lat0):.6f}" lon="{float(lng0):.6f}"><name>Polazak: {escape(tour.meeting_point)}</name></wpt>'
           f'<trk><name>{escape(tour.name)}</name><trkseg>{pts}</trkseg></trk></gpx>')
    resp = HttpResponse(xml, content_type='application/gpx+xml; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="frostbite-tura-{tour.pk}.gpx"'
    resp['Cache-Control'] = 'no-store'
    return resp
