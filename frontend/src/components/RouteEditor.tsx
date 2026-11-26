// Editor rute: klik na mapu dodaje tačku, poništi/obriši, uvoz GPX datoteke.
// SIGURNOST: GPX se čita lokalno (DOMParser kao XML - ništa se ne izvršava) i NE šalje se na server;
// šalju se samo provjerene koordinate (server ih ponovo validira: najviše 500 tačaka, opseg).
import 'leaflet/dist/leaflet.css';
import './map.css';

import L from 'leaflet';
import { useEffect, useRef, useState, type ChangeEvent } from 'react';

import type { LatLng } from '../api/public';
import { MAX_GPX_BYTES, MAX_POINTS, parseGpx, round6 } from '../lib/route';

const BIH_CENTER: LatLng = [43.85, 17.9];
const tileOpts = { referrerPolicy: 'strict-origin-when-cross-origin' } as const;

type Props = { value: LatLng[]; onChange: (route: LatLng[]) => void; error?: string[] | undefined };

export function RouteEditor({ value, onChange, error }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const [gpxError, setGpxError] = useState<string | null>(null);
  const [gpxInfo, setGpxInfo] = useState<string | null>(null);

  useEffect(() => { valueRef.current = value; onChangeRef.current = onChange; }, [value, onChange]);

  useEffect(() => {
    if (!host.current) return;
    const calm = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19, attribution: 'Podloga © Esri, HERE, Garmin, USGS, OpenStreetMap', ...tileOpts,
    });
    const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      maxZoom: 17, subdomains: 'abc', attribution: '© OpenStreetMap, SRTM · © OpenTopoMap (CC-BY-SA)', ...tileOpts,
    });
    const map = L.map(host.current, { layers: [calm], scrollWheelZoom: false }).setView(BIH_CENTER, 8);
    L.control.layers({ 'Prirodna (reljef)': calm, 'Topografska (izohipse)': topo }, undefined, { position: 'topright' }).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
    map.attributionControl.setPrefix(false);
    map.once('focus click', () => map.scrollWheelZoom.enable());
    map.on('click', (e: L.LeafletMouseEvent) => {
      const cur = valueRef.current;
      if (cur.length >= MAX_POINTS) return;
      onChangeRef.current([...cur, [round6(e.latlng.lat), round6(e.latlng.lng)]]);
    });
    layer.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(host.current);
    if (valueRef.current.length >= 2) map.fitBounds(valueRef.current, { padding: [30, 30] });
    return () => { ro.disconnect(); map.remove(); mapRef.current = null; layer.current = null; };
  }, []);

  useEffect(() => {
    const g = layer.current;
    if (!g) return;
    g.clearLayers();
    if (value.length >= 2) L.polyline(value, { className: 'route-line route-line-static', weight: 3, interactive: false }).addTo(g);
    value.forEach((p, i) => {
      const node = document.createElement('span');
      node.className = `edit-point${i === 0 ? ' is-start' : ''}${i === value.length - 1 && i > 0 ? ' is-end' : ''}`;
      L.marker(p, { icon: L.divIcon({ className: 'pin-host', html: node, iconSize: [14, 14], iconAnchor: [7, 7] }), keyboard: false, interactive: false }).addTo(g);
    });
  }, [value]);

  function onFile(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = '';
    setGpxError(null);
    setGpxInfo(null);
    if (!f) return;
    if (f.size > MAX_GPX_BYTES) { setGpxError('GPX datoteka je veća od 5 MB.'); return; }
    f.text().then((text) => {
      const pts = parseGpx(text);
      onChange(pts);
      setGpxInfo(`Uvezeno ${pts.length} tačaka iz „${f.name.slice(0, 60)}“.`);
      mapRef.current?.fitBounds(pts, { padding: [30, 30] });
    }).catch((err: unknown) => setGpxError(err instanceof Error ? err.message : 'GPX nije moguće pročitati.'));
  }

  return (
    <div className="route-editor">
      <div className="route-toolbar">
        <span className="label-mono">Ruta · {value.length}/{MAX_POINTS} tačaka</span>
        <div className="route-actions">
          <button type="button" className="btn btn-ghost btn-sm" disabled={!value.length} onClick={() => onChange(value.slice(0, -1))}>Poništi tačku</button>
          <button type="button" className="btn btn-ghost btn-sm" disabled={!value.length} onClick={() => onChange([])}>Obriši rutu</button>
          <label className="btn btn-ghost btn-sm file-btn">
            Uvezi GPX
            <input type="file" accept=".gpx,application/gpx+xml,application/xml,text/xml" onChange={onFile} />
          </label>
        </div>
      </div>
      <div ref={host} className="map route-map" role="region" aria-label="Mapa za crtanje rute: klik dodaje tačku" />
      <p className="field-hint">Kliknite na mapu da dodate tačke redom od polaska. GPX se čita samo u vašem pregledaču.</p>
      {gpxInfo && <p className="field-hint gpx-ok">{gpxInfo}</p>}
      {gpxError && <p className="field-error" role="alert">{gpxError}</p>}
      {error?.length ? <ul className="field-error">{error.map((e) => <li key={e}>{e}</li>)}</ul> : null}
    </div>
  );
}
