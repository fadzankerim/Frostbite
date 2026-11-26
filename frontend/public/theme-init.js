// Primjena izabrane teme PRIJE iscrtavanja (bez "bljeska" pogrešne teme).
// Vanjska datoteka jer CSP ne dozvoljava inline skripte. Čita samo 'light' ili 'dark'.
(function () {
  try {
    var t = window.localStorage.getItem('fb-theme');
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
  } catch (e) { /* privatni prozor ili blokirana pohrana: prati sistem */ }
})();
