// Crtanje rute ture klikom na mapu (F23). Rezultat se upisuje u skriveno polje "route" kao JSON
// lista [[širina, dužina], ...]. Server ponovo provjerava sve vrijednosti (validate_route).
(function () {
  'use strict';
  var el = document.getElementById('route-editor');
  var input = document.getElementById('id_route');
  if (!el || !input || typeof L === 'undefined') return;

  var MAX_POINTS = 500;
  var points = [];
  try {
    var parsed = JSON.parse(input.value || '[]');
    if (Array.isArray(parsed)) {
      points = parsed.filter(function (p) {
        return Array.isArray(p) && p.length === 2 && isFinite(p[0]) && isFinite(p[1]);
      });
    }
  } catch (e) { points = []; }

  var map = FBMap.create(el).setView([43.85, 17.9], 8);   // Bosna i Hercegovina
  el.classList.add('crosshair');

  var line = L.polyline([], { color: '#2f5d46', weight: 5, opacity: .9 }).addTo(map);
  var markers = L.layerGroup().addTo(map);
  var info = document.getElementById('route-info');

  function km() {
    var d = 0;
    for (var i = 1; i < points.length; i++) {
      d += map.distance(points[i - 1], points[i]);
    }
    return (d / 1000).toFixed(1);
  }

  function dot(latlng, cls) {
    return L.marker(latlng, { keyboard: false, icon: L.divIcon({ className: 'route-dot ' + cls, iconSize: [14, 14], iconAnchor: [7, 7] }) });
  }

  function render() {
    line.setLatLngs(points);
    markers.clearLayers();
    if (points.length) dot(points[0], 'route-start').addTo(markers);
    if (points.length > 1) dot(points[points.length - 1], 'route-end').addTo(markers);
    input.value = JSON.stringify(points.map(function (p) {
      return [Math.round(p[0] * 1e6) / 1e6, Math.round(p[1] * 1e6) / 1e6];
    }));
    if (info) {
      info.textContent = points.length
        ? points.length + ' tačaka · približno ' + km() + ' km'
        : 'Ruta nije ucrtana';
    }
    var start = document.getElementById('route-start');
    if (start) {
      start.hidden = !points.length;
      if (points.length) {
        var c = points[0][0].toFixed(6) + ', ' + points[0][1].toFixed(6);
        document.getElementById('route-start-text').textContent = 'Polazak: ' + c;
        document.getElementById('route-start-link').href =
          'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(c);
      }
    }
  }

  // --- uvoz GPX datoteke (lokalno u pregledniku; datoteka se NE šalje na server) ---
  var MAX_GPX_BYTES = 5 * 1024 * 1024;
  var fileInput = document.getElementById('gpx-file');
  var gpxError = document.getElementById('gpx-error');

  function showError(msg) {
    if (!gpxError) return;
    gpxError.textContent = msg || '';
    gpxError.hidden = !msg;
  }

  // Douglas-Peucker pojednostavljenje uz rastuću toleranciju dok ne bude <= MAX_POINTS tačaka.
  function simplify(pts, tol) {
    if (pts.length < 3) return pts.slice();
    var keep = new Array(pts.length); keep[0] = keep[pts.length - 1] = true;
    var stack = [[0, pts.length - 1]];
    while (stack.length) {
      var seg = stack.pop(), a = pts[seg[0]], b = pts[seg[1]], maxD = 0, idx = -1;
      for (var i = seg[0] + 1; i < seg[1]; i++) {
        var p = pts[i], dx = b[1] - a[1], dy = b[0] - a[0];
        var len = Math.hypot(dx, dy) || 1e-12;
        var d = Math.abs(dy * (p[1] - a[1]) - dx * (p[0] - a[0])) / len;
        if (d > maxD) { maxD = d; idx = i; }
      }
      if (maxD > tol && idx > 0) { keep[idx] = true; stack.push([seg[0], idx], [idx, seg[1]]); }
    }
    return pts.filter(function (_, i) { return keep[i]; });
  }

  function reduce(pts) {
    var tol = 0.00001, out = pts;
    while (out.length > MAX_POINTS && tol < 1) { out = simplify(pts, tol); tol *= 2; }
    return out.slice(0, MAX_POINTS);
  }

  function parseGpx(text) {
    var doc = new DOMParser().parseFromString(text, 'application/xml');
    if (doc.getElementsByTagName('parsererror').length) throw new Error('Datoteka nije ispravan GPX.');
    var nodes = doc.getElementsByTagName('trkpt');
    if (!nodes.length) nodes = doc.getElementsByTagName('rtept');
    var pts = [];
    for (var i = 0; i < nodes.length; i++) {
      var lat = parseFloat(nodes[i].getAttribute('lat')), lng = parseFloat(nodes[i].getAttribute('lon'));
      if (isFinite(lat) && isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) pts.push([lat, lng]);
    }
    if (pts.length < 2) throw new Error('GPX ne sadrži trasu (trkpt ili rtept tačke).');
    return pts;
  }

  if (fileInput) {
    fileInput.addEventListener('change', function () {
      showError('');
      var f = fileInput.files && fileInput.files[0];
      fileInput.value = '';                       // input nema "name" i nikad se ne šalje sa formom
      if (!f) return;
      if (f.size > MAX_GPX_BYTES) { showError('GPX datoteka je veća od 5 MB.'); return; }
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var pts = parseGpx(String(reader.result));
          var orig = pts.length;
          points = reduce(pts);
          render();
          map.fitBounds(line.getBounds(), { padding: [30, 30] });
          if (info && orig > points.length) info.textContent += ' (pojednostavljeno sa ' + orig + ' tačaka)';
        } catch (e) { showError(e.message); }
      };
      reader.onerror = function () { showError('Datoteku nije moguće pročitati.'); };
      reader.readAsText(f);
    });
  }

  map.on('click', function (e) {
    if (points.length >= MAX_POINTS) return;
    points.push([e.latlng.lat, e.latlng.lng]);
    render();
  });
  document.getElementById('route-undo').addEventListener('click', function () { points.pop(); render(); });
  document.getElementById('route-clear').addEventListener('click', function () { points = []; render(); });

  render();
  if (points.length > 1) map.fitBounds(line.getBounds(), { padding: [30, 30] });
})();
