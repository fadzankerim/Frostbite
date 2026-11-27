// Odjava od jedne vrste obavještenja preko linka iz emaila (/obavjestenja/odjava?t=...).
// Odjava se ne radi automatski pri otvaranju stranice (sigurnosni skeneri emaila otvaraju linkove),
// nego tek na klik. Token potpisuje server i važi samo za isključivanje te jedne kategorije.
import { Link, useSearchParams } from 'react-router';

import { useMe } from '../api/auth';
import { ApiError } from '../api/client';
import { useUnsubscribe } from '../api/notifications';
import { Notice } from '../components/forms';
import { Frosti } from '../components/Frosti';
import '../components/notifications.css';
import './pages.css';

export function UnsubscribePage() {
  const [params] = useSearchParams();
  const token = params.get('t') ?? '';
  const unsub = useUnsubscribe();
  const { data: me } = useMe();
  const settingsLink = me?.authenticated ? '/profil#obavjestenja' : `/prijava?next=${encodeURIComponent('/profil#obavjestenja')}`;
  const valid = token.length > 0 && token.length < 500;

  return (
    <section className="container page">
      <div className="unsub">
        <Frosti mood={unsub.isSuccess ? 'happy' : unsub.isError || !valid ? 'sad' : 'think'} size={110} />
        <span className="label-mono">Obavještenja · odjava</span>
        {unsub.isSuccess ? (
          <>
            <h1 className="page-title">Gotovo.</h1>
            <Notice kind="ok">{unsub.data.detail}</Notice>
          </>
        ) : (
          <>
            <h1 className="page-title">Odjava od obavještenja</h1>
            {!valid && <Notice kind="error">Link za odjavu nije potpun. Obavještenja možete podesiti u profilu.</Notice>}
            {unsub.error instanceof ApiError && <Notice kind="error">{unsub.error.detail}</Notice>}
            {valid && !unsub.isError && (
              <>
                <p className="muted">Više nećete dobijati ovu vrstu emaila. Sigurnosna obavještenja o nalogu stižu uvijek.</p>
                <button type="button" className="btn btn-accent" disabled={unsub.isPending} onClick={() => unsub.mutate(token)}>
                  Odjavi me
                </button>
              </>
            )}
          </>
        )}
        <Link className="link" to={settingsLink}>Sve postavke obavještenja →</Link>
      </div>
    </section>
  );
}
