// Leaflet mapa: pinovi tura (lista) ili ruta jedne ture (detalji).
//
// SIGURNOST: nazive tura i društava unose korisnici. Sadržaj pinova i popupa se gradi isključivo
// preko DOM-a i textContent (nikad HTML string), pa ubačeni HTML ostaje običan tekst.
// Domeni podloga moraju biti u CSP img-src (docker/nginx/default.conf, infra/app/04-deploy-app.sh).
import 'leaflet/dist/leaflet.css';
import './map.css';

import L from 'leaflet';
import { useEffect, useRef } from 'react';

import type { DifficultyCode, LatLng } from '../api/public';
import { clearDash } from '../lib/svg';

export type Pin = {
  id: number;
  lat: number;
  lng: number;
  title: string;
  club: string;
  when: string;
  difficulty: DifficultyCode;
  difficultyLabel: string;
  spots: string;
};

type Props = {
  label: string;
  pins?: Pin[];
  route?: LatLng[];
  activeId?: number | null;
  onOpen?: (id: number) => void;
  className?: string;
};

const BIH_CENTER: LatLng = [43.85, 17.9];
const tileOpts = { referrerPolicy: 'strict-origin-when-cross-origin' } as const;

function baseLayers() {
  const calm = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19, attribution: 'Podloga © Esri, HERE, Garmin, USGS, OpenStreetMap', ...tileOpts,
  });
  const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    maxZoom: 17, subdomains: 'abc', attribution: '© OpenStreetMap, SRTM · © OpenTopoMap (CC-BY-SA)', ...tileOpts,
  });
  const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© OpenStreetMap', ...tileOpts,
  });
  return { calm, all: { 'Prirodna (reljef)': calm, 'Topografska (izohipse)': topo, Standardna: osm } };
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

const validLatLng = (lat: number, lng: number) =>
  Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;

function pinIcon(difficulty: string, extra = '') {
  const node = el('span', `pin pin-${difficulty.toLowerCase()} ${extra}`.trim());
  node.appendChild(el('span', 'pin-core'));
  return L.divIcon({ className: 'pin-host', html: node, iconSize: [28, 28], iconAnchor: [14, 14], popupAnchor: [0, -14] });
}

function popupContent(pin: Pin, onOpen?: (id: number) => void): HTMLElement {
  const box = el('div', 'pop');
  const top = el('div', 'pop-top');
  top.appendChild(el('span', `pop-badge d-${pin.difficulty.toLowerCase()}`, pin.difficultyLabel));
  top.appendChild(el('span', 'pop-when', pin.when));
  box.appendChild(top);
  box.appendChild(el('strong', 'pop-title', pin.title));
  box.appendChild(el('span', 'pop-club', pin.club));
  box.appendChild(el('span', 'pop-spots', pin.spots));
  const a = el('a', 'pop-link', 'Detalji ture →');
  a.href = `/ture/${Number(pin.id)}`;
  a.addEventListener('click', (e) => {
    if (!onOpen || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    onOpen(pin.id);
  });
  box.appendChild(a);
  return box;
}

export function MapView({ label, pins, route, activeId, onOpen, className }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const markers = useRef(new Map<number, L.Marker>());
  const onOpenRef = useRef(onOpen);

  useEffect(() => { onOpenRef.current = onOpen; }, [onOpen]);

  // jedna mapa po komponenti
  useEffect(() => {
    if (!host.current) return;
    const layers = baseLayers();
    const map = L.map(host.current, { layers: [layers.calm], scrollWheelZoom: false, zoomControl: true })
      .setView(BIH_CENTER, 8);
    L.control.layers(layers.all, undefined, { position: 'topright' }).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
    map.attributionControl.setPrefix(false);
    // točkić miša zumira tek kad korisnik klikne na mapu (ne "otima" skrolanje stranice)
    map.once('focus click', () => map.scrollWheelZoom.enable());
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(host.current);
    return () => {
      ro.disconnect();
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  // pinovi
  useEffect(() => {
    const map = mapRef.current;
    const group = layerRef.current;
    if (!map || !group || !pins) return;
    group.clearLayers();
    markers.current.clear();
    const bounds: LatLng[] = [];
    for (const p of pins) {
      if (!validLatLng(p.lat, p.lng)) continue;
      const m = L.marker([p.lat, p.lng], { icon: pinIcon(p.difficulty), title: p.title, riseOnHover: true, keyboard: true })
        .bindPopup(popupContent(p, (id) => onOpenRef.current?.(id)), { className: 'fb-popup', minWidth: 220, closeButton: true })
        .addTo(group);
      markers.current.set(p.id, m);
      bounds.push([p.lat, p.lng]);
    }
    if (bounds.length === 1) map.setView(bounds[0]!, 11);
    else if (bounds.length > 1) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
  }, [pins]);

  // ruta
  useEffect(() => {
    const map = mapRef.current;
    const group = layerRef.current;
    if (!map || !group || !route) return;
    group.clearLayers();
    const pts = route.filter(([a, b]) => validLatLng(a, b));
    if (pts.length < 2) return;
    L.polyline(pts, { className: 'route-casing', weight: 7, interactive: false }).addTo(group);
    const line = L.polyline(pts, { className: 'route-line', weight: 3, interactive: false }).addTo(group);
    // normalizovana dužina putanje: animacija iscrtavanja radi za bilo koju dužinu i zum
    const lineEl = line.getElement();
    lineEl?.setAttribute('pathLength', '1');
    lineEl?.addEventListener('animationend', clearDash, { once: true });
    L.marker(pts[0]!, { icon: pinIcon('start', 'pin-start'), title: 'Polazak', keyboard: false }).addTo(group);
    L.marker(pts[pts.length - 1]!, { icon: pinIcon('end', 'pin-end'), title: 'Kraj rute', keyboard: false }).addTo(group);
    map.fitBounds(line.getBounds(), { padding: [32, 32] });
  }, [route]);

  // istaknuti pin (prelaz mišem preko kartice u listi)
  useEffect(() => {
    markers.current.forEach((m, id) => {
      m.getElement()?.classList.toggle('is-active', id === activeId);
      if (id === activeId) m.setZIndexOffset(1000);
      else m.setZIndexOffset(0);
    });
  }, [activeId]);

  return <div ref={host} className={`map${className ? ` ${className}` : ''}`} role="region" aria-label={label} />;
}
