// Mapa svih tura (stranica /ture/). Svaka tura je pin na početku rute; klik otvara popup.
// SIGURNOST: naziv ture i društva unosi korisnik (admin društva), zato se popup gradi
// isključivo preko DOM-a i textContent - nikad innerHTML - pa ubačeni HTML ostaje običan tekst.
(function () {
  'use strict';
  var el = document.getElementById('tours-map');
  var dataEl = document.getElementById('tours-data');
  if (!el || !dataEl || typeof L === 'undefined') return;

  var points = [];
  try { points = JSON.parse(dataEl.textContent) || []; } catch (e) { points = []; }
  points = points.filter(function (p) { return isFinite(p.lat) && isFinite(p.lng); });

  var map = FBMap.create(el, { scrollWheelZoom: false }).setView([43.85, 17.9], 8);
  map.once('focus', function () { map.scrollWheelZoom.enable(); });

  var CLASS = { LAKA: 'd-easy', SREDNJA: 'd-medium', TESKA: 'd-hard', VRLO_TESKA: 'd-extreme' };

  function node(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = String(text);
    return n;
  }

  function popup(p) {
    var box = node('div', 'pop');
    var top = node('div', 'pop-top');
    top.appendChild(node('span', 'badge badge-solid ' + (CLASS[p.difficulty] || ''), p.difficulty_label));
    top.appendChild(node('span', 'pop-date', p.date));
    box.appendChild(top);
    box.appendChild(node('strong', 'pop-name', p.name));
    box.appendChild(node('span', 'pop-club', p.club));
    box.appendChild(node('span', 'pop-spots', p.free > 0 ? p.free + ' slobodnih od ' + p.max : 'Popunjeno · lista čekanja'));
    var a = node('a', 'btn btn-sm pop-btn', 'Vidi detaljno');
    // URL dolazi sa servera (reverse), dodatno dozvoljavamo samo relativne putanje /ture/<broj>/
    a.href = /^\/ture\/\d+\/$/.test(p.url) ? p.url : '#';
    box.appendChild(a);
    return box;
  }

  var markers = {};
  var bounds = [];
  points.forEach(function (p) {
    var icon = L.divIcon({
      className: 'tour-pin ' + (CLASS[p.difficulty] || '') + '-pin',
      html: '<span></span>', iconSize: [30, 38], iconAnchor: [15, 36], popupAnchor: [0, -32]
    });
    var m = L.marker([p.lat, p.lng], { icon: icon, title: p.name, riseOnHover: true })
      .bindPopup(popup(p), { closeButton: true, minWidth: 220, className: 'tour-popup' })
      .addTo(map);
    markers[p.id] = m;
    bounds.push([p.lat, p.lng]);
  });
  if (bounds.length === 1) map.setView(bounds[0], 11);
  else if (bounds.length > 1) map.fitBounds(bounds, { padding: [48, 48], maxZoom: 12 });

  // povezivanje kartica i pinova: prelaz mišem preko kartice ističe pin
  document.querySelectorAll('[data-tour-id]').forEach(function (card) {
    var m = markers[card.getAttribute('data-tour-id')];
    if (!m) return;
    card.addEventListener('mouseenter', function () { var e = m.getElement(); if (e) e.classList.add('pin-active'); });
    card.addEventListener('mouseleave', function () { var e = m.getElement(); if (e) e.classList.remove('pin-active'); });
  });
})();
