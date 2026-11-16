// Zajednički slojevi mape za sve mape u aplikaciji.
// Zadana podloga je mirna, prirodnih tonova sa reljefom (Esri World Topo); topografska i standardna su dostupne u izborniku slojeva.
// Svi domeni podloga moraju biti dozvoljeni u CSP-u (img-src) u Nginx konfiguraciji.
window.FBMap = (function () {
  'use strict';
  var opts = { referrerPolicy: 'strict-origin-when-cross-origin' };

  function layers() {
    var calm = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', Object.assign({
      maxZoom: 19, attribution: 'Podloga © Esri, HERE, Garmin, USGS, OpenStreetMap'
    }, opts));
    var topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', Object.assign({
      maxZoom: 17, subdomains: 'abc', attribution: '© OpenStreetMap, SRTM · © OpenTopoMap (CC-BY-SA)'
    }, opts));
    var osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', Object.assign({
      maxZoom: 19, attribution: '© OpenStreetMap'
    }, opts));
    return { base: calm, all: { 'Prirodna (reljef)': calm, 'Topografska (izohipse)': topo, 'Standardna': osm } };
  }

  // Kreira mapu sa zadanom podlogom i izbornikom slojeva.
  function create(el, mapOptions) {
    var l = layers();
    var map = L.map(el, Object.assign({ layers: [l.base] }, mapOptions || {}));
    L.control.layers(l.all, null, { position: 'topright' }).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
    return map;
  }

  return { create: create };
})();
