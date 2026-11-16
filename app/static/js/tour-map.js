// Prikaz rute ture na mapi (Leaflet). Podaci dolaze iz <script type="application/json" id="map-data">,
// tako da nema inline JavaScript-a (CSP: script-src 'self').
(function () {
  'use strict';
  var el = document.getElementById('tour-map');
  var dataEl = document.getElementById('map-data');
  if (!el || !dataEl || typeof L === 'undefined') return;

  var data = JSON.parse(dataEl.textContent);
  var route = (data.route || []).filter(function (p) {
    return Array.isArray(p) && p.length === 2 && isFinite(p[0]) && isFinite(p[1]);
  });
  if (route.length < 2) return;

  var map = FBMap.create(el, { scrollWheelZoom: false });

  var line = L.polyline(route, { color: '#2f5d46', weight: 5, opacity: 0.9, lineJoin: 'round' }).addTo(map);
  L.polyline(route, { color: '#ffffff', weight: 1.5, opacity: 0.8, dashArray: '4 8' }).addTo(map);

  function dot(latlng, cls, title) {
    return L.marker(latlng, {
      title: title, keyboard: false,
      icon: L.divIcon({ className: 'route-dot ' + cls, iconSize: [16, 16], iconAnchor: [8, 8] })
    }).addTo(map);
  }
  dot(route[0], 'route-start', 'Polazak');
  dot(route[route.length - 1], 'route-end', 'Cilj');

  map.fitBounds(line.getBounds(), { padding: [28, 28] });
  // točkić miša zumira tek nakon klika na mapu (stranica se normalno skrola)
  map.once('focus', function () { map.scrollWheelZoom.enable(); });
})();
