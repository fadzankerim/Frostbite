// Stranice prijave i registracije: prikaz/skrivanje lozinke i indikator jačine lozinke.
// Indikator je samo pomoć korisniku - pravila lozinke provjerava server (Django validatori).
(function () {
  'use strict';
  var SPRITE = document.querySelector('link[rel="icon"][type="image/svg+xml"]');
  var spriteUrl = SPRITE ? SPRITE.getAttribute('href').replace('favicon.svg', 'icons/sprite.svg') : '/static/icons/sprite.svg';

  function icon(name) {
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('class', 'icon'); svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS(ns, 'use');
    use.setAttribute('href', spriteUrl + '#' + name);
    svg.appendChild(use);
    return svg;
  }

  document.querySelectorAll('.auth-form input[type="password"]').forEach(function (input) {
    var wrap = document.createElement('div');
    wrap.className = 'pw-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    var btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'pw-toggle';
    btn.setAttribute('aria-label', 'Prikaži lozinku');
    btn.appendChild(icon('eye'));
    btn.addEventListener('click', function () {
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.setAttribute('aria-label', show ? 'Sakrij lozinku' : 'Prikaži lozinku');
      btn.classList.toggle('on', show);
      btn.replaceChild(icon(show ? 'eye-off' : 'eye'), btn.firstChild);
      input.focus();
    });
    wrap.appendChild(btn);
  });

  var meter = document.querySelector('.strength');
  if (meter) {
    var input = document.getElementById(meter.getAttribute('data-for'));
    var text = meter.querySelector('.strength-text');
    var LABELS = ['Najmanje 10 znakova', 'Slaba', 'Osrednja', 'Dobra', 'Odlična'];
    var update = function () {
      var v = input.value || '';
      var score = 0;
      if (v.length >= 10) {
        score = 1;
        var kinds = [/[a-zšđčćž]/, /[A-ZŠĐČĆŽ]/, /\d/, /[^A-Za-z0-9šđčćžŠĐČĆŽ]/].filter(function (r) { return r.test(v); }).length;
        if (kinds >= 2) score++;
        if (kinds >= 3 && v.length >= 12) score++;
        if (kinds >= 3 && v.length >= 16) score++;
      }
      meter.setAttribute('data-score', String(score));
      text.textContent = LABELS[score];
    };
    input.addEventListener('input', update);
    update();
  }
})();
