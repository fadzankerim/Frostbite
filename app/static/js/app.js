// Učitava se u <head> (bez defer) da bi klasa "js" postojala prije prvog iscrtavanja:
// animacije pojavljivanja se aktiviraju samo kad JavaScript radi; bez njega je sav sadržaj vidljiv.
document.documentElement.classList.add('js');

document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  // senka zaglavlja nakon skrolanja
  var bar = document.querySelector('.topbar');
  if (bar) {
    var onScroll = function () { bar.classList.toggle('scrolled', window.scrollY > 8); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
  // zatvaranje korisničkog menija klikom izvan njega
  document.addEventListener('click', function (e) {
    document.querySelectorAll('details.menu[open]').forEach(function (m) {
      if (!m.contains(e.target)) m.removeAttribute('open');
    });
  });
  // pojavljivanje elemenata pri skrolanju
  var items = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) {
    items.forEach(function (el) { el.classList.add('is-visible'); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) { en.target.classList.add('is-visible'); io.unobserve(en.target); }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  items.forEach(function (el) { io.observe(el); });
});
