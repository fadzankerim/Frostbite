import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import { cleanFilters, useFilterOptions, useTours, type TourFilters } from '../api/public';
import { Notice } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { MapView, tourPins } from '../components/MapView';
import { TourCard } from '../components/TourCard';
import { plural } from '../lib/format';
import './pages.css';

export function ToursPage() {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => cleanFilters(params), [params]);
  const tours = useTours(filters);
  const options = useFilterOptions();
  const navigate = useNavigate();
  const [active, setActive] = useState<number | null>(null);
  const [q, setQ] = useState(filters.q ?? '');

  // pretraga po tekstu: URL se ažurira 300 ms nakon zadnjeg kucanja
  useEffect(() => {
    const trimmed = q.trim();
    if ((filters.q ?? '') === trimmed) return;
    const t = window.setTimeout(() => {
      setParams((prev) => {
        const next = new URLSearchParams(prev);
        if (trimmed) next.set('q', trimmed);
        else next.delete('q');
        return next;
      }, { replace: true });
    }, 300);
    return () => window.clearTimeout(t);
  }, [q, filters.q, setParams]);

  function update(patch: Partial<Record<keyof TourFilters, string | undefined>>) {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      for (const [k, v] of Object.entries(patch)) {
        if (v) next.set(k, v);
        else next.delete(k);
      }
      return next;
    }, { replace: true });
  }

  function reset() {
    setQ('');
    setParams(new URLSearchParams(), { replace: true });
  }

  const list = useMemo(() => tours.data ?? [], [tours.data]);
  const pins = useMemo(() => tourPins(list), [list]);
  const withoutRoute = list.length - pins.length;
  const filtered = Object.keys(filters).length > 0;

  return (
    <div className="tours-page">
      <section className="tours-list-col">
        <header className="tours-head">
          <span className="label-mono">Ture · Narednih 30 dana</span>
          <h1 className="page-title">
            {tours.isPending ? 'Ture' : `${list.length} ${plural(list.length, ['tura', 'ture', 'tura'])}`}
          </h1>
        </header>

        <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
          <label className="sr-only" htmlFor="f-q">Pretraga</label>
          <input id="f-q" className="input filter-q" type="search" placeholder="Naziv ture ili regija"
            value={q} onChange={(e) => setQ(e.target.value)} maxLength={80} autoComplete="off" />

          <div className="chips-row" role="group" aria-label="Težina">
            <button type="button" className={`chip-btn${!filters.difficulty ? ' is-on' : ''}`}
              aria-pressed={!filters.difficulty} onClick={() => update({ difficulty: undefined })}>Sve</button>
            {options.data?.difficulties.map((d) => (
              <button key={d.code} type="button" aria-pressed={filters.difficulty === d.code}
                className={`chip-btn chip-${d.code.toLowerCase()}${filters.difficulty === d.code ? ' is-on' : ''}`}
                onClick={() => update({ difficulty: filters.difficulty === d.code ? undefined : d.code })}>
                <span className="diff-dot" aria-hidden="true" />{d.label}
              </button>
            ))}
          </div>

          <div className="filter-row">
            <label className="field">
              <span className="field-label">Društvo</span>
              <select className="input" value={filters.club ?? ''} onChange={(e) => update({ club: e.target.value || undefined })}>
                <option value="">Sva društva</option>
                {options.data?.clubs.map((c) => <option key={c.id} value={String(c.id)}>{c.name}</option>)}
              </select>
            </label>
            <label className="field">
              <span className="field-label">Od</span>
              <input className="input" type="date" value={filters.date_from ?? ''}
                onChange={(e) => update({ date_from: e.target.value || undefined })} />
            </label>
            <label className="field">
              <span className="field-label">Do</span>
              <input className="input" type="date" value={filters.date_to ?? ''}
                onChange={(e) => update({ date_to: e.target.value || undefined })} />
            </label>
          </div>
          {filtered && <button type="button" className="btn btn-ghost btn-sm" onClick={reset}>Poništi filtere</button>}
        </form>

        {tours.isError && <Notice kind="error">Ture nije moguće učitati. Provjerite filtere ili pokušajte ponovo.</Notice>}

        <div className={`tour-list${tours.isFetching && !tours.isPending ? ' is-refreshing' : ''}`} aria-busy={tours.isFetching}>
          {tours.isPending && Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton" />)}
          {!tours.isPending && list.length === 0 && !tours.isError && (
            <div className="empty">
              <Frosti mood="think" size={96} />
              <span className="label-mono">Nema rezultata</span>
              <p className="muted">{filtered ? 'Nijedna tura ne odgovara filterima.' : 'Trenutno nema objavljenih tura u narednih 30 dana.'}</p>
            </div>
          )}
          {list.map((t, i) => <TourCard key={t.id} tour={t} index={i} onHover={setActive} />)}
        </div>
        {withoutRoute > 0 && <p className="label-mono list-note">{withoutRoute} bez ucrtane rute (nisu na mapi)</p>}
      </section>

      <aside className="tours-map-col">
        <div className="tours-map-sticky frame">
          <div className="frame-bar">
            <span className="label-mono"><span className="live-dot" />{pins.length} na mapi</span>
            <span className="label-mono hide-sm">Klik na pin za detalje</span>
          </div>
          <div className="frame-map">
            <MapView label="Mapa tura" pins={pins} activeId={active} onOpen={(id) => navigate(`/ture/${id}`)} />
          </div>
        </div>
      </aside>
    </div>
  );
}
